# Template Upgrade Plan - Achieving Parity

Based on the audit, here's what needs to be added to `sony_open_preview.html` to match `docs/shopify-embed.html`:

## Missing Components

### 1. **Crew Picks Section** ⭐ PRIORITY
**What**: Featured section showing crew member betting picks
**Where**: Between event info and betting board
**Components**:
- Section header with title "Cosmos Crew Picks"
- Grid layout (1→2→4 columns responsive)
- 4 crew member cards with:
  - Circular profile photo (80px with glow effect)
  - Name with text shadow
  - 3 picks each (Win, Top 5, Top 10)
  - Hover animations

**CSS Required**: ~150 lines
**HTML Required**: ~50 lines
**Data Needed**:
- 4 crew member photos
- 12 total picks (3 per person)

### 2. **Section Headers Component** ⭐ PRIORITY
**What**: Styled section dividers with line
**Where**: Before Crew Picks and Complete Betting Board
**Components**:
- H2 title
- Decorative line extending to fill width
- Flex layout

**CSS Required**: ~30 lines
**Already in docs/shopify-embed.html**: Lines 346-369

### 3. **Full Responsive Design** ⭐ CRITICAL
**Current**: Only 1 media query at 1200px
**Needed**: 5 responsive breakpoints

**Breakpoints to add**:
```css
@media (min-width: 480px)  /* Small mobile */
@media (min-width: 768px)  /* Tablet */
@media (min-width: 1024px) /* Desktop */
@media (min-width: 1440px) /* Large desktop */
@media (min-width: 1200px) /* Full width Shopify */
```

**What scales**:
- Container padding: 15px → 20px → 30px → 40px
- Header h1: 28px → 32px → 36px → 42px
- Logo height: 50px → 60px → 70px → 85px
- Crew grid columns: 1 → 2 → 4
- Table padding: 12px/8px → 14px/10px → 16px/12px → 18px/12px
- Font sizes throughout

### 4. **Advanced CSS Effects**
**Missing hover effects**:
- Crew card elevation on hover
- Photo glow intensification
- Radial gradient overlay
- Diagonal shine effect on crew picks container

**Missing animations**:
- Transform: `translateY(-2px)` on hover
- Scale: `scale(1.05)` on photo hover
- Box shadow transitions

### 5. **Extended Player List**
**Current**: 33 players
**Target**: 119 players (full field)
**Missing**: 86 player rows

## Implementation Plan

### Phase 1: Core Structure (30 min)
1. Add section header component CSS and HTML
2. Add crew picks section structure
3. Insert placeholder crew data

### Phase 2: Styling & Effects (45 min)
4. Add crew picks CSS (~150 lines)
5. Add hover effects and animations
6. Test crew picks display

### Phase 3: Responsive Design (60 min)
7. Add 4 missing media query breakpoints
8. Scale all components at each breakpoint
9. Test on mobile, tablet, desktop

### Phase 4: Content (30 min)
10. Add crew member photos
11. Add crew picks data
12. Verify all data displays correctly

### Phase 5: Extended Players (optional)
13. Add remaining 86 player rows with data

## Quick Win Approach

**Minimum for Parity** (just add these 2 sections):
1. **Section Headers** - 10 min
2. **Crew Picks** - 30 min
3. **Basic Responsive** - 20 min

**Total time**: ~60 minutes for core parity

## Files to Update

1. **sony_open_preview.html** - Add all missing components
2. **scripts/generate_html.py** - Update template to include crew picks
3. **Template data structure** - Add crew picks to JSON

## Data Structure for Crew Picks

```json
{
  "crew_picks": [
    {
      "name": "Miller",
      "photo_url": "/path/to/miller.jpg",
      "picks": [
        {"type": "Win", "player": "J.J. Spaun", "odds": "+1800"},
        {"type": "Top 5", "player": "Robert MacIntyre", "odds": "+400"},
        {"type": "Top 10", "player": "Si Woo Kim", "odds": "+200"}
      ]
    },
    // ... 3 more crew members
  ]
}
```

## Next Steps

1. **Option A - Manual Update**: Copy sections from docs/shopify-embed.html to sony_open_preview.html
2. **Option B - Generate Script**: Update generate_html.py to create complete template
3. **Option C - Hybrid**: Manually add to sony_open_preview.html, then update generator

**Recommendation**: Option C (Hybrid)
- Quick manual update for immediate parity
- Then update generator for future automation
- Best of both worlds

---

**Status**: Ready to implement
**Priority**: High (user requested parity)
**Complexity**: Medium (mostly copy-paste + data)
**Time**: 60-90 minutes for full parity
