#!/usr/bin/env bash
# Frees disk space used by cached downloads and old indexes.
# Usage: CACHE_DIR=data/cache ./scripts/prune_cache.sh

rm -rf "$CACHE_DIR"/*
echo "pruned $CACHE_DIR"
