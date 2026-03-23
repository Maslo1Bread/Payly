from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth import get_current_user
from ..database import get_db
from ..email_keyword_parser import normalize_service_name, parse_subscription_candidate
from ..email_providers import GmailProvider, MailRuProvider
from ..provider_token_store import OAuthStateStore, ProviderTokenStore

router = APIRouter(prefix="/integrations", tags=["integrations"])

_BACKEND_DIR = Path(__file__).resolve().parent.parent

_STATE_STORE = OAuthStateStore(
    key_path=_BACKEND_DIR / ".oauth_state.key",
    data_path=_BACKEND_DIR / ".oauth_state.enc",
)
_PROVIDER_TOKEN_STORE = ProviderTokenStore(
    key_path=_BACKEND_DIR / ".provider_tokens.key",
    data_path=_BACKEND_DIR / ".provider_tokens.enc",
)


def _frontend_base_url() -> str:
    return os.getenv("PAYLY_FRONTEND_BASE_URL", "http://127.0.0.1:8001")


def _backend_base_url(request: Optional[Request] = None) -> str:
    env_url = os.getenv("PAYLY_BACKEND_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    if request is not None:
        return str(request.base_url).rstrip("/")
    return "http://127.0.0.1:8000"


def _redirect_uri(provider: str, request: Optional[Request] = None) -> str:
    return f"{_backend_base_url(request)}/integrations/{provider}/oauth/callback"


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Missing env var {name}",
        )
    return val


def _get_provider(provider: str, request: Optional[Request] = None):
    provider = provider.lower()
    if provider == "gmail":
        client_id = _require_env("GMAIL_CLIENT_ID")
        client_secret = _require_env("GMAIL_CLIENT_SECRET")
        return GmailProvider(client_id=client_id, client_secret=client_secret, redirect_uri=_redirect_uri(provider, request))
    if provider == "mailru":
        client_id = _require_env("MAILRU_CLIENT_ID")
        client_secret = _require_env("MAILRU_CLIENT_SECRET")
        return MailRuProvider(client_id=client_id, client_secret=client_secret, redirect_uri=_redirect_uri(provider, request))
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown provider")


@router.post("/{provider}/oauth/start", response_model=schemas.OAuthStartOut)
def oauth_start(
    provider: str,
    request: Request,
    client: str = Query("web"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    provider = provider.lower()
    if provider not in {"gmail", "mailru"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider")

    state = secrets.token_urlsafe(32)
    code_verifier: Optional[str] = None
    if provider == "gmail":
        # PKCE: Google OAuth требует code_verifier при обмене кода на токены.
        # Нужен один и тот же verifier на oauth/start и oauth/callback.
        code_verifier = secrets.token_urlsafe(64)[:100]

    _STATE_STORE.put(state=state, user_id=current_user.id, provider=provider, code_verifier=code_verifier, client=client)

    p = _get_provider(provider, request)
    try:
        authorization_url = p.build_authorization_url(state=state, code_verifier=code_verifier)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return schemas.OAuthStartOut(authorization_url=authorization_url)


@router.get("/{provider}/oauth/callback")
def oauth_callback(
    provider: str,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
):
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code/state")

    provider = provider.lower()
    record = _STATE_STORE.pop(state=state)
    if not record or record.get("provider") != provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state")

    user_id = record.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid oauth state record")
    code_verifier = record.get("code_verifier")

    p = _get_provider(provider, request)
    try:
        refresh_token = p.exchange_code_for_refresh_token(code=code, code_verifier=code_verifier)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Token exchange failed: {e}")

    _PROVIDER_TOKEN_STORE.set_refresh_token(user_id=int(user_id), provider=provider, refresh_token=refresh_token)

    client = (record.get("client") or "web").lower()
    if client == "mobile":
        from fastapi.responses import HTMLResponse

        return HTMLResponse(
            content=f"""
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Payly — почта подключена</title>
    <style>
      body {{ font-family: Arial, sans-serif; background: linear-gradient(135deg, #0f172a, #312e81); color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; }}
      .card {{ width: min(92vw, 540px); background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.14); border-radius: 24px; padding: 28px; box-shadow: 0 20px 60px rgba(0,0,0,0.28); }}
      h1 {{ margin: 0 0 12px; font-size: 28px; }}
      p {{ line-height: 1.5; color: rgba(255,255,255,0.88); }}
      .ok {{ display: inline-flex; align-items: center; gap: 10px; background: rgba(16,185,129,0.15); color: #a7f3d0; border: 1px solid rgba(16,185,129,0.35); padding: 10px 14px; border-radius: 999px; margin-bottom: 18px; }}
    </style>
  </head>
  <body>
    <div class="card">
      <div class="ok">✓ Почта {provider} успешно подключена</div>
      <h1>Возвращайтесь в приложение Payly</h1>
      <p>Теперь можно закрыть браузер и нажать в приложении кнопку "Проверить импорт" или "Импортировать из почты".</p>
    </div>
  </body>
</html>
            """,
            status_code=status.HTTP_200_OK,
        )

    redirect_url = f"{_frontend_base_url()}/content.html?connected=1&provider={provider}"
    # Redirect "в лоб" как строка, т.к. в учебном проекте нет шаблонов.
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.post("/{provider}/sync-subscriptions", response_model=schemas.SyncSubscriptionsResultOut)
def sync_subscriptions(
    provider: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    provider = provider.lower()
    if provider not in {"gmail", "mailru"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider")

    token_record = _PROVIDER_TOKEN_STORE.get(user_id=current_user.id, provider=provider)
    if not token_record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider not connected")

    p = _get_provider(provider)

    # Если первый sync — берем небольшой диапазон.
    last_synced_at = token_record.last_synced_at
    if not last_synced_at:
        last_synced_at = datetime.utcnow() - timedelta(days=60)

    limit = 25
    candidates = []
    msg_dates: list[datetime] = []

    try:
        if provider == "gmail":
            messages = list(p.list_messages(refresh_token=token_record.refresh_token, last_synced_at=last_synced_at, limit=limit))
        else:
            messages = list(
                p.list_messages(
                    user_email=current_user.email,
                    refresh_token=token_record.refresh_token,
                    last_synced_at=last_synced_at,
                    limit=limit,
                )
            )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Fetch messages failed: {e}")

    for m in messages:
        msg_dates.append(m.internal_date)
        parsed = parse_subscription_candidate(
            subject=m.subject,
            text=m.body_text,
            received_at=m.internal_date,
        )
        if not parsed:
            continue
        candidates.append(parsed)

    existing = crud.get_subscriptions_for_user(db, user_id=current_user.id)
    existing_by_norm = {}
    for s in existing:
        n = normalize_service_name(s.name)
        # Если уже есть дубликаты по нормализованному названию — берем самый свежий.
        if n not in existing_by_norm or (existing_by_norm[n].created_at < s.created_at):
            existing_by_norm[n] = s

    created = 0
    updated = 0
    skipped = 0

    for cand in candidates:
        n = normalize_service_name(cand.name)
        if n in existing_by_norm:
            sub = existing_by_norm[n]
            updated_in = schemas.SubscriptionUpdate(
                name=cand.name,
                price=cand.price,
                billing_cycle=cand.billing_cycle,
                next_payment_date=cand.next_payment_date,
            )
            ok = crud.update_subscription_for_user(
                db,
                subscription_id=sub.id,
                user_id=current_user.id,
                subscription_in=updated_in,
            )
            if ok:
                updated += 1
            else:
                skipped += 1
        else:
            create_in = schemas.SubscriptionCreate(
                name=cand.name,
                price=cand.price,
                billing_cycle=cand.billing_cycle,
                next_payment_date=cand.next_payment_date,
            )
            created_sub = crud.create_subscription(db, user_id=current_user.id, subscription_in=create_in)
            if created_sub:
                created += 1
                existing_by_norm[n] = created_sub
            else:
                skipped += 1

    if msg_dates:
        _PROVIDER_TOKEN_STORE.set_last_synced_at(
            user_id=current_user.id,
            provider=provider,
            last_synced_at=max(msg_dates),
        )

    return schemas.SyncSubscriptionsResultOut(
        provider=provider,
        created=created,
        updated=updated,
        skipped=skipped,
        items=crud.get_subscriptions_for_user(db, user_id=current_user.id),
    )


def _parse_candidates_from_messages(
    *,
    provider: str,
    messages: list,
) -> list[dict]:
    """
    Превращает сообщения в список кандидатов подписок.
    """
    out: list[dict] = []
    for m in messages:
        parsed = parse_subscription_candidate(
            subject=m.subject,
            text=m.body_text,
            received_at=m.internal_date,
        )
        if not parsed:
            continue

        normalized = normalize_service_name(parsed.name)
        candidate_key = f"{normalized}|{parsed.next_payment_date.isoformat()}|{round(parsed.price, 2)}|{m.message_id}"
        out.append(
            {
                "candidate_key": candidate_key,
                "service_normalized": normalized,
                "name": parsed.name,
                "price": float(parsed.price),
                "billing_cycle": parsed.billing_cycle,
                "next_payment_date": parsed.next_payment_date,
                "source_message_id": m.message_id,
            }
        )
    return out


def _fetch_messages(
    *,
    provider: str,
    current_user,
    token_record: ProviderTokenStore,
    last_synced_at: datetime,
    limit: int,
):
    p = _get_provider(provider)

    if provider == "gmail":
        return list(p.list_messages(refresh_token=token_record.refresh_token, last_synced_at=last_synced_at, limit=limit))

    return list(
        p.list_messages(
            user_email=current_user.email,
            refresh_token=token_record.refresh_token,
            last_synced_at=last_synced_at,
            limit=limit,
        )
    )


@router.post("/{provider}/sync-subscriptions/preview", response_model=schemas.SyncSubscriptionsPreviewResultOut)
def sync_subscriptions_preview(
    provider: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    provider = provider.lower()
    if provider not in {"gmail", "mailru"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider")

    token_record = _PROVIDER_TOKEN_STORE.get(user_id=current_user.id, provider=provider)
    if not token_record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider not connected")

    last_synced_at = token_record.last_synced_at
    if not last_synced_at:
        last_synced_at = datetime.utcnow() - timedelta(days=60)

    limit = 25
    try:
        messages = _fetch_messages(
            provider=provider,
            current_user=current_user,
            token_record=token_record,
            last_synced_at=last_synced_at,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Fetch messages failed: {e}")

    candidates = _parse_candidates_from_messages(provider=provider, messages=messages)
    return schemas.SyncSubscriptionsPreviewResultOut(
        provider=provider,
        candidates=[
            schemas.SubscriptionCandidateOut(
                candidate_key=c["candidate_key"],
                name=c["name"],
                price=c["price"],
                billing_cycle=c["billing_cycle"],
                next_payment_date=c["next_payment_date"],
            )
            for c in candidates
        ],
    )


@router.post("/{provider}/sync-subscriptions/import", response_model=schemas.SyncSubscriptionsResultOut)
def sync_subscriptions_import(
    provider: str,
    import_in: schemas.SyncSubscriptionsImportIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    provider = provider.lower()
    if provider not in {"gmail", "mailru"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider")

    token_record = _PROVIDER_TOKEN_STORE.get(user_id=current_user.id, provider=provider)
    if not token_record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider not connected")

    last_synced_at = token_record.last_synced_at
    if not last_synced_at:
        last_synced_at = datetime.utcnow() - timedelta(days=60)

    limit = 25
    try:
        messages = _fetch_messages(
            provider=provider,
            current_user=current_user,
            token_record=token_record,
            last_synced_at=last_synced_at,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Fetch messages failed: {e}")

    all_candidates = _parse_candidates_from_messages(provider=provider, messages=messages)
    selected_keys = set(import_in.candidate_keys or [])
    selected = [c for c in all_candidates if c["candidate_key"] in selected_keys]

    # Дедуп кандидатам: оставляем лучший next_payment_date на normalized service name.
    best_by_norm: dict[str, dict] = {}
    for c in selected:
        norm = c["service_normalized"]
        if norm not in best_by_norm or best_by_norm[norm]["next_payment_date"] < c["next_payment_date"]:
            best_by_norm[norm] = c

    existing = crud.get_subscriptions_for_user(db, user_id=current_user.id)
    existing_by_norm: dict[str, object] = {}
    for s in existing:
        n = normalize_service_name(s.name)
        if n not in existing_by_norm or existing_by_norm[n].created_at < s.created_at:
            existing_by_norm[n] = s

    created = 0
    updated = 0
    skipped = 0

    msg_dates: list[datetime] = []
    for c in best_by_norm.values():
        msg_dates.append(datetime.utcnow())
        norm = c["service_normalized"]
        if norm in existing_by_norm:
            sub = existing_by_norm[norm]
            updated_in = schemas.SubscriptionUpdate(
                name=c["name"],
                price=c["price"],
                billing_cycle=c["billing_cycle"],
                next_payment_date=c["next_payment_date"],
            )
            ok = crud.update_subscription_for_user(
                db,
                subscription_id=sub.id,
                user_id=current_user.id,
                subscription_in=updated_in,
            )
            if ok:
                updated += 1
            else:
                skipped += 1
        else:
            create_in = schemas.SubscriptionCreate(
                name=c["name"],
                price=c["price"],
                billing_cycle=c["billing_cycle"],
                next_payment_date=c["next_payment_date"],
            )
            created_sub = crud.create_subscription(db, user_id=current_user.id, subscription_in=create_in)
            if created_sub:
                created += 1
                existing_by_norm[norm] = created_sub
            else:
                skipped += 1

    # Обновляем last_synced_at на максимально внутреннюю дату среди сообщений (если распарсилось хоть что-то).
    if messages:
        last_date = max([m.internal_date for m in messages if getattr(m, "internal_date", None)], default=None)
        if last_date:
            _PROVIDER_TOKEN_STORE.set_last_synced_at(user_id=current_user.id, provider=provider, last_synced_at=last_date)

    return schemas.SyncSubscriptionsResultOut(
        provider=provider,
        created=created,
        updated=updated,
        skipped=skipped,
        items=crud.get_subscriptions_for_user(db, user_id=current_user.id),
    )

