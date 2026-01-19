# COSMOS Golf Betting Preview

A space-themed, interactive golf betting preview website for PGA Tour events. This project features a futuristic NASA-inspired design with comprehensive player analysis, historical results, and betting odds.

## 🚀 Overview

COSMOS Golf Betting Preview provides detailed betting analysis for PGA Tour events with a unique space-themed aesthetic. The preview includes player storylines, historical course performance, betting odds, and visual design elements that create an immersive experience.

## 📁 Project Structure

```
CosmosGolfBetting/
├── README.md                      # This file
├── sony_open_preview.html         # Standalone preview page for 2026 Sony Open
├── shopify-embed.html             # Shopify-compatible embed version
├── COSMOS_Golf-Dec-Logo_001.png   # Main logo (color)
├── COSMOS_Golf-Dec-Logo_001_White.png  # White logo variant
└── waialae.jpg                    # Course image (Waialae Country Club)
```

## 🎨 Features

### Design Elements
- **Space-themed UI**: NASA-inspired color palette with cyber-cyan, grid-green, and space-black
- **Animated backgrounds**: Radial gradients and grid overlays for depth
- **Typography**: Orbitron, Rajdhani, and Share Tech Mono fonts for futuristic feel
- **Responsive design**: Works on desktop and mobile devices

### Content Features
- **Complete betting board**: Comprehensive player rankings with odds
- **Historical results**: 3-year course history for each player
- **Player storylines**: Detailed analysis of why each player could win
- **Tier badges**: Visual categorization (Favorite, Contender, Value Play, Longshot)
- **Asian player highlights**: Special indicators for Asian players
- **Event information**: Purse, course details, field size, and more

## 📄 Files Description

### `sony_open_preview.html`
A standalone HTML file for the 2026 Sony Open at Waialae Country Club. This is a complete, self-contained preview page that can be opened directly in a browser or hosted on any web server.

**Features:**
- Full-page betting preview
- 33 players with detailed analysis
- Historical results (2023-2025)
- Win, Top 5, and Top 10 odds
- Course image and event details

### `shopify-embed.html`
A Shopify-compatible version designed to be embedded into a Shopify store page. This version uses scoped CSS classes to prevent style conflicts with Shopify themes.

**Usage:**
1. Upload images to Shopify Files (Settings > Files):
   - `COSMOS_Golf-Dec-Logo_001.png`
   - `waialae.jpg`
2. Copy the image URLs from Shopify Files
3. Replace the image URLs in the HTML with your Shopify file URLs
4. In Shopify Admin:
   - Go to Online Store > Pages > Add page
   - Or add to an existing page using a Custom HTML section
   - Paste the entire code block

## 🎯 Color Palette

The design uses a consistent NASA-inspired color scheme:

- **NASA Blue**: `#0B3D91` - Primary brand color
- **NASA Red**: `#FC3D21` - Accent color
- **Space Black**: `#0a0a0f` - Background
- **Cyber Cyan**: `#00d4ff` - Primary accent, text highlights
- **Grid Green**: `#00ff88` - Success states, wins
- **Warning Gold**: `#ffd700` - Favorites, top 5 finishes

## 📊 Data Structure

The preview includes:
- **Event Information**: Total purse, winner's share, course details, field size
- **Player Data**: Name, country, OWGR ranking, tier classification
- **Historical Results**: 3-year course history with color-coded results
- **Betting Odds**: Win, Top 5, and Top 10 odds from DraftKings Sportsbook
- **Storylines**: Detailed analysis of each player's chances

## 🛠️ Customization

### Updating Player Data
Edit the HTML table in either file to update:
- Player names and rankings
- Historical results
- Betting odds
- Storyline text

### Changing Events
To create a preview for a different tournament:
1. Update the event name and dates in the header
2. Replace the course image
3. Update course details (yardage, par, etc.)
4. Modify player data and storylines
5. Update event information panel

### Styling
All styles are contained within `<style>` tags. Key customization points:
- Color variables in `:root` (or `.cosmos-betting-preview` for Shopify version)
- Font families in the Google Fonts link
- Grid and background effects in `::before` and `::after` pseudo-elements

## 📱 Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Responsive design for mobile devices
- Uses CSS Grid and Flexbox
- Google Fonts for typography

## 📝 Notes

- Odds are sourced from DraftKings Sportsbook (as of January 12, 2026 for Sony Open)
- Data is for entertainment purposes only
- Includes responsible gambling disclaimer
- All player links open Google search results

## 🔮 Future Enhancements

Potential additions:
- Interactive filtering and sorting
- Player comparison tool
- Historical trend analysis
- Live odds updates
- Multiple tournament support
- Dark/light mode toggle

## 📄 License

This project is for COSMOS Golf use. All rights reserved.

---

**COSMOS Golf · Golf in the Cosmos · 2026 Season Preview**
