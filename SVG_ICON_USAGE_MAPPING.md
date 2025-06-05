# SVG Icon Usage Mapping - Complete Analysis

## Duplicate Icon Folders Found! 🚨

**Issue**: Icons are duplicated in two locations:
- `resources/icons/` - **31 icons**
- `src/jcselect/resources/icons/` - **17 icons**

## Icon Usage Mapping

### 📋 Admin Dashboard (`src/jcselect/ui/AdminDashboard.qml`)

**Header/Menu Icons:**
- `refresh.svg` - Line 78: Refresh button
- `user-management.svg` - Line 112: User management menu item
- `settings.svg` - Line 122: Settings menu item  
- `switch-user.svg` - Line 134: Switch user menu item
- `logout.svg` - Line 144: Logout menu item

**Quick Stats MetricCards:**
- `search-voters.svg` - Line 169: Total registered voters metric
- `ballot-count.svg` - Line 180: Total votes cast metric
- `tally-count.svg` - Line 191: Active tally sessions metric
- `sync-status.svg` - Line 202: Pending sync operations metric

**Main Dashboard CardTiles:**
- `voter-search.svg` - Line 232: **Voter Search & Check-in tile**
- `ballot-count.svg` - Line 255: **Vote Counting tile**
- `live-results.svg` - Line 279: **Live Results tile**
- `sync-status.svg` - Line 303: **Sync Status tile**
- `audit-logs.svg` - Line 320: **Audit Logs tile**
- `system-settings.svg` - Line 338: **System Settings tile**

**Error Display:**
- `error.svg` - Line 362: Error message icon

### 📋 Operator Dashboard (`src/jcselect/ui/OperatorDashboard.qml`)

**Header Icons:**
- `switch-user.svg` - Line 92: Switch user button

**Quick Stats MetricCards:**
- `search-voters.svg` - Line 116: Total voters metric
- `pending-voters.svg` - Line 127: **⚠️ MISSING ICON!** Remaining voters metric  
- `tally-count.svg` - Line 138: Active sessions metric

**Main Dashboard CardTiles:**
- `voter-search.svg` - Line 161: **Voter Search & Check-in tile**
- `ballot-count.svg` - Line 185: **Tally Counting tile**
- `turnout-stats.svg` - Line 210: **Turnout Reports tile**
- `sync-status.svg` - Line 227: **Sync Status tile**

**Error Display:**
- `error.svg` - Line 255: Error message icon

### 📋 Test Files
- `test.svg` - Used in GUI tests (`tests/gui/test_card_tile.qml`)

## 🔍 Icon Analysis

### Icons Used Multiple Times:
1. **`sync-status.svg`** - Used 4 times (both dashboards, metrics + tiles)
2. **`ballot-count.svg`** - Used 3 times (admin metrics + both dashboard tiles)
3. **`voter-search.svg`** - Used 2 times (both dashboard main tiles)
4. **`tally-count.svg`** - Used 2 times (both dashboard metrics)
5. **`error.svg`** - Used 2 times (both dashboard error displays)
6. **`switch-user.svg`** - Used 2 times (both dashboard headers)

### Icons Used Once:
- `refresh.svg` - Admin refresh button
- `user-management.svg` - Admin user menu
- `settings.svg` - Admin settings menu
- `logout.svg` - Admin logout menu
- `search-voters.svg` - Admin voter stats metric
- `live-results.svg` - Admin live results tile
- `audit-logs.svg` - Admin audit logs tile
- `system-settings.svg` - Admin system settings tile
- `turnout-stats.svg` - Operator turnout reports tile

### ⚠️ Missing Icons:
- **`pending-voters.svg`** - Referenced in OperatorDashboard line 127 but doesn't exist!

### 📁 Icons Only in Main Folder (`resources/icons/`):
- `online.svg`, `offline.svg`, `syncing.svg` - Sync status indicators
- `success.svg` - Success states
- `filter.svg`, `export.svg` - UI operations  
- `results-charts.svg`, `winners.svg` - Results display
- `count-ops.svg`, `badge-success.svg` - Counting operations
- `sync-online.svg`, `sync-offline.svg` - Sync states
- `pen-picker.svg`, `user-menu.svg` - UI components

### 📁 Icons Only in Duplicate Folder (`src/jcselect/resources/icons/`):
- `warning-alert.svg` - Alert states (269KB - suspiciously large!)
- `test.svg` - Testing purposes

## 🎯 Issues Identified

### 1. **Duplicate Folders**
Icons are stored in two locations with partial overlap, causing confusion.

### 2. **Missing Icon**
`pending-voters.svg` is referenced but doesn't exist anywhere.

### 3. **Potential Icon Misuse**
- `search-voters.svg` vs `voter-search.svg` - Similar names, different purposes?
- Large file size for `warning-alert.svg` (269KB vs typical ~600B)

### 4. **Unused Icons**
Many icons in the main folder aren't referenced in the current codebase.

## 📝 Recommendations

1. **Consolidate to Single Folder**: Move all icons to `resources/icons/` and remove duplicates
2. **Create Missing Icon**: Add `pending-voters.svg` for the operator dashboard
3. **Review Icon Usage**: Verify correct icons are used for their intended purposes
4. **Clean Up**: Remove unused icons or document their intended use
5. **Fix Large File**: Check why `warning-alert.svg` is 269KB 