#!/bin/bash
echo "--- Générateur de Commit ---"
read -p "Type (feat/fix/chore): " TYPE
read -p "Scope (ex: admin/pari): " SCOPE
read -p "Message: " MSG

git commit -m "$TYPE($SCOPE): $MSG"

