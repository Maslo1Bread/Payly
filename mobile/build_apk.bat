@echo off
cd /d %~dp0
npm install
npx eas-cli build --platform android --profile preview
