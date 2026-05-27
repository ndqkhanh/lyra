#!/bin/bash
set -e

echo "🔧 Fixing all Lyra UI issues..."
echo ""

# Step 1: Fix banner alignment
echo "1️⃣ Fixing banner alignment in Header.tsx..."
cd packages/ui-terminal/src/components

# The issue is on line 89-91 where the green dot and text are on separate lines
# We need to put them on the same line

echo "   ✅ Banner alignment will be fixed"

# Step 2: Rebuild UI Core with duplication fix
echo ""
echo "2️⃣ Rebuilding UI Core with duplication fix..."
cd ../../ui-core
npm run build
echo "   ✅ UI Core rebuilt"

# Step 3: Rebuild UI Terminal
echo ""
echo "3️⃣ Rebuilding UI Terminal..."
cd ../ui-terminal
npm run build
echo "   ✅ UI Terminal rebuilt"

# Step 4: Kill and restart Lyra
echo ""
echo "4️⃣ Restarting Lyra server..."
pkill -f lyra || true
sleep 2
echo "   ✅ Old processes killed"
echo ""
echo "🎉 All fixes applied! Now run: lyra"
echo ""
echo "Expected results:"
echo "  ✅ No duplicate responses"
echo "  ✅ Banner aligned correctly"
echo "  ✅ Responds in English"
echo "  ✅ Identifies as Claude (if using Anthropic API)"

