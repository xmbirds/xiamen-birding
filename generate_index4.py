# -*- coding: utf-8 -*-
import json
import os
from spots_data_1109 import INTRO_DATA, SPOTS_1109

OUT_DIR = "/Users/libo/xmbirds/birdspoint"

# Overview image dimensions (from 1109/厦门市观鸟点分布图20261109c.jpg & e.jpg -> PNG)
OVERVIEW_W = 1968
OVERVIEW_H = 1901

# Single-spot local map image dimensions (from 1110/*.bmp -> PNG)
LOCAL_IMG_W = 1200
LOCAL_IMG_H = 800

habitat_pin_colors = {
    "coastal": "#1565C0",
    "wetland": "#00838F",
    "forest": "#388E3C",
    "mountain": "#1B5E20",
}

# Build interactive SVG hotspot overlay for the 1968x1901 official overview map image
# Covers both the ①-⑨ red circles on the map AND the ①-⑨ legend rows in the bottom-right corner!
hotspot_els = []
for idx, s in enumerate(SPOTS_1109):
    sid = s["id"]
    cx, cy = s.get("overview_px", [984, 950])
    leg_y = 1405 + idx * 48 - 22
    hotspot_els.append(f'''            <g class="overview-hotspot" data-id="{sid}" tabindex="0" role="button" aria-label="{s['num']} {s['name_zh']}" onclick="selectSpot({sid})">
              <circle class="hotspot-pulse" cx="{cx}" cy="{cy}" r="26" />
              <circle class="hotspot-ring" cx="{cx}" cy="{cy}" r="22" />
              <circle class="hotspot-hit" cx="{cx}" cy="{cy}" r="44" />
              <rect class="legend-hit" x="1488" y="{leg_y}" width="452" height="44" rx="8" ry="8" />
            </g>''')

overview_hotspots_svg_str = "\n".join(hotspot_els)


def build_index4_page(default_lang="zh"):
    is_en = (default_lang == "en")
    html_lang = "en" if is_en else "zh-CN"
    page_title = INTRO_DATA["title_en"] if is_en else INTRO_DATA["title_zh"]
    initial_overview_src = "assets_1110/overview_en.png" if is_en else "assets_1110/overview_zh.png"

    return f'''<!DOCTYPE html>
<html lang="{html_lang}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=4.0, user-scalable=yes" />
  <title>{page_title}</title>
  <style>
    :root {{
      --page-bg: #edf4f9;
      --header-grad-top: #d6e8f5;
      --header-border: #b5cfe3;
      --card-bg: #ffffff;
      --ink-dark: #183045;
      --ink-muted: #4b657d;
      --accent-main: #1b6592;
      --accent-red: #d93025;
      --border-color: #cbddec;
      --frame-border: #9bc0dc;
      --toolbar-border: #b0cce3;
      --thead-bg: #dfeef8;
      --row-hover: #f2f8fc;
      --chip-bg: #ebf5f0;
      --chip-text: #1f6349;
      --chip-border: #c0dfd0;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
    body {{
      background-color: var(--page-bg);
      color: var(--ink-dark);
      font-family: "PingFang SC", "Hiragino Sans GB", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.62;
      padding-bottom: 54px;
    }}

    .handbook-header {{
      max-width: 920px;
      margin: 0 auto;
      padding: 18px 18px 16px;
      border-bottom: 2px solid var(--header-border);
      background: linear-gradient(180deg, var(--header-grad-top) 0%, var(--page-bg) 100%);
    }}
    .badge-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .org-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--accent-main);
      color: #fff;
      font-size: 12.5px;
      font-weight: 600;
      padding: 4px 11px;
      border-radius: 6px;
      letter-spacing: 0.4px;
    }}
    .lang-switch {{
      display: inline-flex;
      background: #d7e7f4;
      border: 1px solid #9bc0dc;
      border-radius: 20px;
      padding: 2px;
      gap: 2px;
      flex-shrink: 0;
    }}
    .lang-btn {{
      border: none;
      background: transparent;
      color: var(--ink-muted);
      font-size: 12.5px;
      font-weight: 700;
      padding: 4px 12px;
      border-radius: 16px;
      cursor: pointer;
      transition: all 0.18s;
    }}
    .lang-btn.active {{
      background: var(--accent-main);
      color: #ffffff;
      box-shadow: 0 1px 4px rgba(27, 101, 146, 0.3);
    }}

    .handbook-title {{
      font-family: "Songti SC", "STSong", "Noto Serif SC", Georgia, serif;
      font-size: 25px;
      font-weight: 800;
      color: var(--ink-dark);
      letter-spacing: 0.8px;
      margin-bottom: 10px;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-bottom: 12px;
    }}
    .stat-card {{
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 7px 10px;
      text-align: center;
    }}
    .stat-num {{
      font-size: 17px;
      font-weight: 800;
      color: var(--accent-main);
      line-height: 1.25;
    }}
    .stat-label {{
      font-size: 11.5px;
      color: var(--ink-muted);
      margin-top: 2px;
    }}
    .handbook-lead {{
      font-size: 13.8px;
      color: var(--ink-dark);
      opacity: 0.92;
      text-align: justify;
    }}
    .handbook-lead p + p {{
      margin-top: 6px;
    }}

    /* Overview Map Image + Interactive SVG Hotspot Overlay */
    .map-section {{
      max-width: 920px;
      margin: 14px auto 0;
      padding: 0 14px;
    }}
    .map-frame {{
      position: relative;
      width: 100%;
      border: 2px solid var(--frame-border);
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 6px 20px rgba(30, 45, 55, 0.09);
      background: #ffffff;
    }}
    .overview-img-stage {{
      position: relative;
      width: 100%;
      line-height: 0;
      background: #f5f2e9;
    }}
    .overview-map-img {{
      display: block;
      width: 100%;
      height: auto;
      user-select: none;
    }}
    .overview-hotspots-svg {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      z-index: 5;
    }}
    .overview-hotspot {{
      cursor: pointer;
      outline: none;
    }}
    .overview-hotspot .hotspot-hit {{
      fill: rgba(217, 48, 37, 0.001);
      stroke: none;
    }}
    .overview-hotspot .hotspot-ring {{
      fill: rgba(255, 235, 59, 0.01);
      stroke: #ff9800;
      stroke-width: 4px;
      opacity: 0;
      transition: all 0.2s ease;
    }}
    .overview-hotspot .hotspot-pulse {{
      fill: none;
      stroke: #d93025;
      stroke-width: 4px;
      opacity: 0;
      transform-origin: center;
      transform-box: fill-box;
    }}
    .overview-hotspot .legend-hit {{
      fill: rgba(217, 48, 37, 0.001);
      stroke: transparent;
      stroke-width: 2.5px;
      transition: all 0.18s ease;
    }}
    .overview-hotspot:hover .hotspot-ring,
    .overview-hotspot.active .hotspot-ring {{
      fill: rgba(255, 221, 87, 0.34);
      stroke: #ff9800;
      stroke-width: 5px;
      stroke-dasharray: none;
      opacity: 1;
    }}
    .overview-hotspot:hover .legend-hit,
    .overview-hotspot.active .legend-hit {{
      fill: rgba(255, 235, 59, 0.22);
      stroke: #d93025;
    }}
    .overview-hotspot.active .hotspot-pulse {{
      opacity: 1;
      animation: hotspotPulseAnim 1.5s infinite ease-out;
    }}
    @keyframes hotspotPulseAnim {{
      0% {{ transform: scale(0.9); opacity: 0.95; }}
      100% {{ transform: scale(2.15); opacity: 0; }}
    }}

    .map-hint-bar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 9px 14px;
      background: rgba(255, 253, 248, 0.96);
      border-top: 1px solid var(--border-color);
      font-size: 12.5px;
      color: var(--ink-dark);
    }}
    .zoom-img-btn {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: #ebf4fb;
      color: var(--accent-main);
      border: 1px solid #a9cbe4;
      border-radius: 6px;
      padding: 3.5px 10px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .zoom-img-btn:hover {{
      background: var(--accent-main);
      color: #ffffff;
    }}

    /* Table / List Section */
    .table-section {{
      max-width: 920px;
      margin: 18px auto 0;
      padding: 0 14px;
    }}
    .section-head {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .section-title {{
      font-family: "Songti SC", "STSong", Georgia, serif;
      font-size: 19px;
      font-weight: 800;
      color: var(--ink-dark);
    }}
    .filter-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .filter-pill {{
      border: 1px solid var(--toolbar-border);
      background: var(--card-bg);
      color: var(--ink-muted);
      font-size: 12px;
      font-weight: 600;
      padding: 4.5px 11px;
      border-radius: 16px;
      cursor: pointer;
    }}
    .filter-pill.active {{
      background: var(--accent-main);
      color: #fff;
      border-color: var(--accent-main);
    }}

    .table-card {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 3px 10px rgba(0,0,0,0.04);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13.5px;
    }}
    thead {{
      background: var(--thead-bg);
      color: var(--ink-dark);
      text-align: left;
    }}
    th, td {{
      padding: 12px 14px;
      border-bottom: 1px solid var(--border-color);
      vertical-align: middle;
    }}
    tbody tr {{
      cursor: pointer;
      transition: background 0.15s;
    }}
    tbody tr:hover {{ background: var(--row-hover); }}
    tbody tr.active-row {{ background: #fff3d6; }}
    .num-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      border-radius: 50%;
      color: #fff;
      font-weight: 700;
      font-size: 12.5px;
    }}
    .spot-title-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }}
    .spot-link {{
      color: #1c4e63;
      font-weight: 700;
      font-size: 15px;
    }}
    .row-arrow {{
      color: var(--ink-muted);
      font-size: 17px;
      font-weight: 700;
      opacity: 0.45;
      flex-shrink: 0;
    }}
    .spot-submeta {{
      font-size: 12.5px;
      color: var(--ink-muted);
      margin-top: 3px;
    }}
    .mobile-birds-wrap {{
      display: none;
      margin-top: 7px;
    }}
    .bird-chip {{
      display: inline-block;
      background: var(--chip-bg);
      color: var(--chip-text);
      border: 1px solid var(--chip-border);
      border-radius: 4px;
      padding: 1.5px 7px;
      font-size: 12px;
      margin: 2px 4px 2px 0;
      white-space: nowrap;
    }}
    .bird-chip.highlight-chip {{
      background: #fff4e5;
      color: #9a3412;
      border-color: #f6cca2;
      font-weight: 600;
    }}

    @media (max-width: 680px) {{
      .handbook-title {{ font-size: 21px; }}
      .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
      thead {{ display: none; }}
      th.col-habitat, td.col-habitat,
      th.col-birds, td.col-birds {{
        display: none;
      }}
      td {{ padding: 13px 12px; }}
      td.col-num {{
        width: 42px;
        padding-right: 4px;
        vertical-align: top;
        padding-top: 15px;
      }}
      .mobile-birds-wrap {{ display: block; }}
    }}

    /* Detail Sheet Modal */
    .card-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(20, 28, 32, 0.48);
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s ease;
      z-index: 90;
    }}
    .card-backdrop.open {{
      opacity: 1;
      pointer-events: auto;
    }}
    .spot-sheet {{
      position: fixed;
      left: 50%;
      bottom: 0;
      transform: translate(-50%, 105%);
      width: 100%;
      max-width: 740px;
      max-height: 88vh;
      overflow-y: auto;
      background: var(--card-bg);
      border-top: 4px solid var(--accent-red);
      border-radius: 18px 18px 0 0;
      box-shadow: 0 -8px 30px rgba(0,0,0,0.24);
      padding: 18px 18px 28px;
      transition: transform 0.28s cubic-bezier(0.2, 0.9, 0.3, 1);
      z-index: 100;
    }}
    .spot-sheet.open {{
      transform: translate(-50%, 0);
    }}
    .sheet-header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }}
    .sheet-title-wrap {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .sheet-num {{
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: var(--accent-red);
      color: #fff;
      font-weight: 800;
      font-size: 16px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }}
    .sheet-title {{
      font-family: "Songti SC", "STSong", Georgia, serif;
      font-size: 19.5px;
      font-weight: 800;
      color: var(--ink-dark);
    }}
    .close-btn {{
      border: 1px solid var(--border-color);
      background: var(--page-bg);
      color: var(--ink-muted);
      width: 32px;
      height: 32px;
      border-radius: 50%;
      font-size: 18px;
      cursor: pointer;
      flex-shrink: 0;
    }}
    .meta-grid {{
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-bottom: 12px;
    }}
    .meta-tag {{
      font-size: 12px;
      padding: 3.5px 9px;
      border-radius: 5px;
      background: var(--thead-bg);
      color: var(--ink-dark);
      font-weight: 600;
    }}

    /* Official PNG Local Map Box inside Sheet */
    .local-map-box {{
      border: 1.5px solid var(--frame-border);
      border-radius: 10px;
      overflow: hidden;
      background: #1d2d22;
      margin-bottom: 12px;
    }}
    .local-map-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 6px;
      padding: 7px 12px;
      background: #dfeef8;
      border-bottom: 1px solid var(--border-color);
      font-size: 12.5px;
      font-weight: 700;
      color: var(--ink-dark);
    }}
    .local-img-stage {{
      position: relative;
      width: 100%;
      line-height: 0;
      background: #233329;
    }}
    .local-spot-img {{
      display: block;
      width: 100%;
      height: auto;
      cursor: zoom-in;
    }}
    .local-subspot-svg {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
    }}
    .subspot-hit-link {{
      pointer-events: auto;
      cursor: pointer;
    }}
    .subspot-hit-circle {{
      fill: rgba(255, 235, 59, 0.01);
      stroke: #ffeb3b;
      stroke-width: 3.5px;
      opacity: 0;
      transition: all 0.18s;
    }}
    .subspot-hit-link:hover .subspot-hit-circle {{
      fill: rgba(255, 235, 59, 0.32);
      stroke: #ffffff;
      stroke-width: 4px;
      stroke-dasharray: none;
      opacity: 1;
    }}
    .subspots-bar {{
      padding: 8px 11px;
      background: #f5f9fc;
      border-top: 1px solid var(--border-color);
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
    }}
    .subspot-nav-pill {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      font-weight: 600;
      color: #1b6592;
      background: #ffffff;
      border: 1px solid #a9cbe4;
      border-radius: 15px;
      padding: 3px 10px;
      text-decoration: none;
      transition: all 0.15s;
    }}
    .subspot-nav-pill:hover {{
      background: #1b6592;
      color: #ffffff;
    }}

    .sheet-desc {{
      font-size: 14px;
      color: var(--ink-dark);
      background: var(--page-bg);
      border-left: 3.5px solid var(--accent-main);
      padding: 10px 13px;
      border-radius: 0 8px 8px 0;
      margin-bottom: 12px;
      text-align: justify;
    }}
    .sheet-desc p + p {{ margin-top: 7px; }}

    .info-block {{
      font-size: 13px;
      color: var(--ink-dark);
      margin-bottom: 9px;
      background: #f8fbfd;
      border: 1px solid #d9e8f4;
      padding: 8px 11px;
      border-radius: 7px;
    }}
    .bird-group-row {{
      margin-bottom: 7px;
    }}
    .bird-group-label {{
      font-size: 12.5px;
      font-weight: 700;
      color: var(--ink-muted);
      margin-right: 6px;
    }}
    .sheet-tips {{
      font-size: 13px;
      color: #5b4628;
      background: #fff6e0;
      border: 1px dashed #dfbe78;
      padding: 9px 12px;
      border-radius: 7px;
      margin-top: 10px;
    }}
    .sheet-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }}
    .btn-primary, .btn-amap {{
      flex: 1;
      min-width: 140px;
      text-align: center;
      padding: 11px 14px;
      border-radius: 8px;
      font-size: 13.5px;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
      border: none;
    }}
    .btn-primary {{ background: #1b6592; color: #ffffff; }}
    .btn-amap {{ background: #2d6a4f; color: #ffffff; }}

    /* Fullscreen Image Lightbox */
    .lightbox-modal {{
      position: fixed;
      inset: 0;
      background: rgba(10, 16, 22, 0.92);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 16px;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.22s ease;
      z-index: 200;
    }}
    .lightbox-modal.open {{
      opacity: 1;
      pointer-events: auto;
    }}
    .lightbox-img {{
      max-width: 96vw;
      max-height: 84vh;
      object-fit: contain;
      border-radius: 8px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      background: #fff;
    }}
    .lightbox-caption {{
      margin-top: 10px;
      color: #e2eef8;
      font-size: 13.5px;
      font-weight: 600;
      text-align: center;
    }}
    .lightbox-close {{
      position: absolute;
      top: 16px;
      right: 18px;
      width: 38px;
      height: 38px;
      border-radius: 50%;
      border: 1px solid rgba(255,255,255,0.35);
      background: rgba(0,0,0,0.5);
      color: #fff;
      font-size: 22px;
      cursor: pointer;
    }}

    /* Editorial Credits Footer */
    .credits-section {{
      max-width: 920px;
      margin: 22px auto 0;
      padding: 0 14px;
    }}
    .credits-card {{
      background: linear-gradient(180deg, #f7fbfe 0%, #ffffff 100%);
      border: 1px solid var(--border-color);
      border-top: 3px solid var(--accent-main);
      border-radius: 10px;
      padding: 16px 18px 14px;
      box-shadow: 0 3px 10px rgba(24, 48, 69, 0.04);
    }}
    .credits-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
      padding-bottom: 10px;
      margin-bottom: 12px;
      border-bottom: 1px dashed var(--border-color);
    }}
    .credits-title {{
      font-family: "Songti SC", "STSong", Georgia, serif;
      font-size: 15px;
      font-weight: 800;
      color: var(--ink-dark);
      letter-spacing: 0.5px;
    }}
    .credits-sub {{
      font-size: 12px;
      color: var(--ink-muted);
    }}
    .credits-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }}
    .credit-group {{
      background: rgba(237, 244, 249, 0.65);
      border: 1px solid #d7e7f4;
      border-radius: 8px;
      padding: 10px 12px;
    }}
    .credit-role {{
      font-size: 12px;
      font-weight: 700;
      color: var(--ink-muted);
      margin-bottom: 7px;
      display: flex;
      align-items: center;
      gap: 5px;
    }}
    .credit-people {{
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
    }}
    .author-pill {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      background: #ffffff;
      border: 1px solid #c5dced;
      border-radius: 6px;
      padding: 3.5px 9px;
      font-size: 13px;
      color: var(--ink-dark);
      box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }}
    .author-name {{
      font-weight: 700;
    }}
    .author-nick {{
      font-size: 11.5px;
      font-weight: 600;
      color: #1f6349;
      background: #ebf5f0;
      border: 1px solid #c0dfd0;
      border-radius: 4px;
      padding: 0.5px 6px;
    }}
    @media (max-width: 680px) {{
      .credits-grid {{
        grid-template-columns: 1fr;
        gap: 8px;
      }}
    }}
  </style>
</head>
<body>

  <header class="handbook-header">
    <div class="badge-row">
      <span class="org-badge" id="orgBadgeText"></span>
      <div class="lang-switch" role="tablist" aria-label="Language Switch">
        <button class="lang-btn" id="btnLangZh" onclick="setLanguage('zh')">中文</button>
        <button class="lang-btn" id="btnLangEn" onclick="setLanguage('en')">EN</button>
      </div>
    </div>
    <h1 class="handbook-title" id="mainTitleText"></h1>
    <div class="stats-grid" id="statsGrid"></div>
    <div class="handbook-lead" id="introLead"></div>
  </header>

  <main id="mainOverview">
    <section class="map-section">
      <div class="map-frame">
        <div class="overview-img-stage">
          <img id="overviewMapImg" class="overview-map-img" src="{initial_overview_src}" alt="{page_title}" width="{OVERVIEW_W}" height="{OVERVIEW_H}" />
          <svg id="overviewHotspotsSvg" class="overview-hotspots-svg" viewBox="0 0 {OVERVIEW_W} {OVERVIEW_H}" xmlns="http://www.w3.org/2000/svg">
{overview_hotspots_svg_str}
          </svg>
        </div>
        <div class="map-hint-bar">
          <span id="mapHintText"></span>
          <button class="zoom-img-btn" id="btnZoomOverview" onclick="openOverviewLightbox()"></button>
        </div>
      </div>
    </section>

    <section class="table-section">
      <div class="section-head">
        <h2 class="section-title" id="tableSectionTitle"></h2>
        <div class="filter-pills" id="filterPills"></div>
      </div>

      <div class="table-card">
        <table>
          <thead>
            <tr id="tableHeadRow"></tr>
          </thead>
          <tbody id="spotsTableBody"></tbody>
        </table>
      </div>
    </section>

    <section class="credits-section" id="creditsSection"></section>
  </main>

  <div id="cardBackdrop" class="card-backdrop" onclick="closeCard()"></div>
  <aside id="spotSheet" class="spot-sheet" aria-live="polite"></aside>

  <div id="lightboxModal" class="lightbox-modal" onclick="closeLightbox()">
    <button class="lightbox-close" aria-label="Close" onclick="closeLightbox()">×</button>
    <img id="lightboxImg" class="lightbox-img" src="" alt="" onclick="event.stopPropagation()" />
    <div id="lightboxCaption" class="lightbox-caption"></div>
  </div>

  <script>
    const INTRO = {json.dumps(INTRO_DATA, ensure_ascii=False)};
    const SPOTS = {json.dumps(SPOTS_1109, ensure_ascii=False)};
    const PIN_COLORS = {json.dumps(habitat_pin_colors, ensure_ascii=False)};

    let currentLang = '{default_lang}';
    const urlLang = new URLSearchParams(window.location.search).get('lang');
    if (urlLang === 'en' || urlLang === 'zh') {{
      currentLang = urlLang;
    }}

    let currentFilter = 'all';
    let currentOpenSpotId = null;

    const UI_TEXT = {{
      zh: {{
        mapHint: '👆 点击总图上的 ①—⑨ 红圈或右下角图例名称，即可弹出对应观鸟点图文详情与单点导览图',
        btnZoomOverview: '🔍 放大查看总图',
        btnZoomLocal: '🔍 放大查看原图',
        tableTitle: '📋 厦门九大观鸟点导览（五大区域）',
        filters: [
          {{ key: 'all', label: '全部 (9)' }},
          {{ key: 'island', label: '厦门岛（思明·湖里）' }},
          {{ key: 'haicang', label: '海沧区' }},
          {{ key: 'jimei', label: '集美区' }},
          {{ key: 'tongan', label: '同安区' }},
          {{ key: 'xiangan', label: '翔安区' }}
        ],
        thNum: '编号',
        thSpot: '观鸟点',
        thHabitat: '生境与最佳月份',
        thBirds: '代表及高光鸟种',
        localMapTitle: '🗺️ 观鸟点卫星导览图（点击红圈可导航子点位）',
        subspotsNavLabel: '📍 子观鸟点一键导航：',
        labelDuration: '⏱️ 建议时长：',
        labelMonths: '📅 最佳月份：',
        labelTransport: '🚌 交通方式：',
        labelDifficulty: '🥾 难度系数：',
        labelTip: '💡 观鸟提示：',
        btnTencent: '🧭 腾讯地图导航 (微信推荐)',
        btnAmap: '🗺️ 高德地图导航'
      }},
      en: {{
        mapHint: '👆 Tap any numbered red circle ①–⑨ on the map or in the bottom-right legend to open the hotspot guide',
        btnZoomOverview: '🔍 Zoom Full Map',
        btnZoomLocal: '🔍 Enlarge Image',
        tableTitle: '📋 9 Birding Hotspots in Xiamen (5 Areas)',
        filters: [
          {{ key: 'all', label: 'All (9)' }},
          {{ key: 'island', label: 'Xiamen Island (Siming & Huli)' }},
          {{ key: 'haicang', label: 'Haicang' }},
          {{ key: 'jimei', label: 'Jimei' }},
          {{ key: 'tongan', label: "Tong'an" }},
          {{ key: 'xiangan', label: "Xiang'an" }}
        ],
        thNum: 'No.',
        thSpot: 'Birding Hotspot',
        thHabitat: 'Habitat & Best Months',
        thBirds: 'Key & Notable Birds',
        localMapTitle: '🗺️ Satellite Guide Map (Tap red circles to navigate)',
        subspotsNavLabel: '📍 Navigate to Sub-sites:',
        labelDuration: '⏱️ Duration: ',
        labelMonths: '📅 Best Months: ',
        labelTransport: '🚌 Getting There: ',
        labelDifficulty: '🥾 Difficulty: ',
        labelTip: '💡 Birding Tip: ',
        btnTencent: '🧭 Tencent Maps (WeChat)',
        btnAmap: '🗺️ Amap Navigation'
      }}
    }};

    function openLightbox(src, caption) {{
      const modal = document.getElementById('lightboxModal');
      document.getElementById('lightboxImg').src = src;
      document.getElementById('lightboxCaption').textContent = caption || '';
      modal.classList.add('open');
    }}

    function openOverviewLightbox() {{
      const isEn = (currentLang === 'en');
      const src = isEn ? 'assets_1110/overview_en.png' : 'assets_1110/overview_zh.png';
      const cap = isEn ? INTRO.title_en : INTRO.title_zh;
      openLightbox(src, cap);
    }}

    function closeLightbox() {{
      document.getElementById('lightboxModal').classList.remove('open');
    }}

    function renderHeaderAndMap() {{
      const isEn = (currentLang === 'en');
      document.documentElement.lang = isEn ? 'en' : 'zh-CN';
      document.title = isEn ? INTRO.title_en : INTRO.title_zh;

      document.getElementById('btnLangZh').classList.toggle('active', !isEn);
      document.getElementById('btnLangEn').classList.toggle('active', isEn);

      document.getElementById('orgBadgeText').textContent = isEn ? INTRO.org_en : INTRO.org_zh;
      document.getElementById('mainTitleText').textContent = isEn ? INTRO.title_en : INTRO.title_zh;

      const stats = isEn ? INTRO.stats_en : INTRO.stats_zh;
      document.getElementById('statsGrid').innerHTML = stats.map(st => `
        <div class="stat-card">
          <div class="stat-num">${{st.num}}</div>
          <div class="stat-label">${{st.label}}</div>
        </div>
      `).join('');

      const paras = isEn ? INTRO.paragraphs_en : INTRO.paragraphs_zh;
      document.getElementById('introLead').innerHTML = paras.map(p => `<p>${{p}}</p>`).join('');

      const overviewImg = document.getElementById('overviewMapImg');
      overviewImg.src = isEn ? 'assets_1110/overview_en.png' : 'assets_1110/overview_zh.png';
      overviewImg.alt = isEn ? INTRO.title_en : INTRO.title_zh;

      const t = UI_TEXT[currentLang];
      document.getElementById('mapHintText').textContent = t.mapHint;
      document.getElementById('btnZoomOverview').textContent = t.btnZoomOverview;

      document.getElementById('tableSectionTitle').textContent = t.tableTitle;
      document.getElementById('filterPills').innerHTML = t.filters.map(f => `
        <button class="filter-pill ${{currentFilter === f.key ? 'active' : ''}}" onclick="filterTable('${{f.key}}')">${{f.label}}</button>
      `).join('');

      document.getElementById('tableHeadRow').innerHTML = `
        <th style="width:54px">${{t.thNum}}</th>
        <th>${{t.thSpot}}</th>
        <th class="col-habitat" style="width:190px">${{t.thHabitat}}</th>
        <th class="col-birds" style="width:270px">${{t.thBirds}}</th>
      `;

      document.getElementById('creditsSection').innerHTML = isEn ? `
        <div class="credits-card">
          <div class="credits-header">
            <span class="credits-title">🐦 Credits & Editorial Team · Xiamen BirdWatching Society</span>
            <span class="credits-sub">Please keep a safe distance and watch birds quietly</span>
          </div>
          <div class="credits-grid">
            <div class="credit-group">
              <div class="credit-role">🗺️ Map Production</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">Liu Jie (刘杰)</span><span class="author-nick">猫行天下</span></span>
              </div>
            </div>
            <div class="credit-group">
              <div class="credit-role">✍️ Text & Guide</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">Chen Yuhan (陈雨晗)</span><span class="author-nick">Hans</span></span>
                <span class="author-pill"><span class="author-name">Li Xiang (李享)</span><span class="author-nick">无足之鸟</span></span>
              </div>
            </div>
            <div class="credit-group">
              <div class="credit-role">🔍 Proofreading & Review</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">Chen Yuesheng (陈跃生)</span><span class="author-nick">林鸮</span></span>
                <span class="author-pill"><span class="author-name">Liu Xin (刘昕)</span><span class="author-nick">流小星</span></span>
                <span class="author-pill"><span class="author-name">Chen Zhihong (陈志鸿)</span><span class="author-nick">岩鹭</span></span>
              </div>
            </div>
          </div>
        </div>
      ` : `
        <div class="credits-card">
          <div class="credits-header">
            <span class="credits-title">🐦 厦门全域观鸟地图 · 创作与编校团队</span>
            <span class="credits-sub">厦门市观鸟协会 出品 · 保持安全距离，文明安静观鸟</span>
          </div>
          <div class="credits-grid">
            <div class="credit-group">
              <div class="credit-role">🗺️ 地图制作</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">刘杰</span><span class="author-nick">猫行天下</span></span>
              </div>
            </div>
            <div class="credit-group">
              <div class="credit-role">✍️ 文字介绍</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">陈雨晗</span><span class="author-nick">Hans</span></span>
                <span class="author-pill"><span class="author-name">李享</span><span class="author-nick">无足之鸟</span></span>
              </div>
            </div>
            <div class="credit-group">
              <div class="credit-role">🔍 校对审核</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">陈跃生</span><span class="author-nick">林鸮</span></span>
                <span class="author-pill"><span class="author-name">刘昕</span><span class="author-nick">流小星</span></span>
                <span class="author-pill"><span class="author-name">陈志鸿</span><span class="author-nick">岩鹭</span></span>
              </div>
            </div>
          </div>
        </div>
      `;
    }}

    function renderTable() {{
      const isEn = (currentLang === 'en');
      const tbody = document.getElementById('spotsTableBody');
      const filtered = currentFilter === 'all'
        ? SPOTS
        : SPOTS.filter(s => s.area_key === currentFilter);

      tbody.innerHTML = filtered.map(s => {{
        const c = PIN_COLORS[s.habitat_tag] || '#b5382a';
        const name = isEn ? s.name_en : s.name_zh;
        const dist = isEn ? s.district_en : s.district_zh;
        const summary = isEn ? s.summary_en : s.summary_zh;
        const hab = isEn ? s.habitat_en : s.habitat_zh;
        const months = isEn ? s.months_en : s.months_zh;
        const birds = isEn ? s.key_birds_en : s.key_birds_zh;
        const birdsHtml = birds.map(b => `<span class="bird-chip">${{b}}</span>`).join('');

        return `
          <tr id="row-${{s.id}}" class="${{currentOpenSpotId === s.id ? 'active-row' : ''}}" onclick="selectSpot(${{s.id}})">
            <td class="col-num"><span class="num-badge" style="background:${{c}}">${{s.id}}</span></td>
            <td>
              <div class="spot-title-row">
                <span class="spot-link">${{name}}</span>
                <span class="row-arrow">›</span>
              </div>
              <div class="spot-submeta">${{dist}} · ${{s.difficulty_stars}} · ${{summary}}</div>
              <div class="mobile-birds-wrap">${{birdsHtml}}</div>
            </td>
            <td class="col-habitat" style="font-size:12.5px;color:var(--ink-muted)">
              <div style="font-weight:600;color:var(--ink-dark)">${{hab}}</div>
              <div style="margin-top:2px">${{months}}</div>
            </td>
            <td class="col-birds">${{birdsHtml}}</td>
          </tr>
        `;
      }}).join('');
    }}

    function filterTable(key) {{
      currentFilter = key;
      renderHeaderAndMap();
      renderTable();
    }}

    function selectSpot(id) {{
      const spot = SPOTS.find(s => s.id === id);
      if (!spot) return;
      currentOpenSpotId = id;
      const isEn = (currentLang === 'en');
      const t = UI_TEXT[currentLang];

      document.querySelectorAll('.overview-hotspot').forEach(m => {{
        m.classList.toggle('active', Number(m.dataset.id) === id);
      }});
      document.querySelectorAll('#spotsTableBody tr').forEach(r => {{
        r.classList.toggle('active-row', r.id === `row-${{id}}`);
      }});

      const c = PIN_COLORS[spot.habitat_tag] || '#b5382a';
      const name = isEn ? spot.name_en : spot.name_zh;
      const dist = isEn ? spot.district_en : spot.district_zh;
      const hab = isEn ? spot.habitat_en : spot.habitat_zh;
      const dur = isEn ? spot.duration_en : spot.duration_zh;
      const months = isEn ? spot.months_en : spot.months_zh;
      const descList = isEn ? spot.desc_en : spot.desc_zh;
      const transport = isEn ? spot.transport_en : spot.transport_zh;
      const diff = isEn ? spot.difficulty_en : spot.difficulty_zh;
      const groups = isEn ? spot.bird_groups_en : spot.bird_groups_zh;
      const tips = isEn ? spot.tips_en : spot.tips_zh;

      const localImgSrc = `assets_1110/spot_${{spot.id}}_${{isEn ? 'en' : 'zh'}}.png`;

      const subspots = spot.local_map.subspots || [];
      const subspotsNavHtml = subspots.map(sub => {{
        const subName = isEn ? sub.en : sub.zh;
        const navUrl = `https://apis.map.qq.com/uri/v1/marker?marker=coord:${{sub.gcj_lat}},${{sub.gcj_lon}};title:${{encodeURIComponent(name + ' - ' + subName)}};addr:${{encodeURIComponent('厦门市' + spot.district_zh)}}&referer=xmbirds`;
        return `<a class="subspot-nav-pill" href="${{navUrl}}" target="_blank" rel="noopener">⭕ ${{subName}} ↗</a>`;
      }}).join('');

      const subspotsSvgHits = subspots.filter(sub => Array.isArray(sub.img_px)).map(sub => {{
        const subName = isEn ? sub.en : sub.zh;
        const [px, py] = sub.img_px;
        const navUrl = `https://apis.map.qq.com/uri/v1/marker?marker=coord:${{sub.gcj_lat}},${{sub.gcj_lon}};title:${{encodeURIComponent(name + ' - ' + subName)}};addr:${{encodeURIComponent('厦门市' + spot.district_zh)}}&referer=xmbirds`;
        return `<a class="subspot-hit-link" href="${{navUrl}}" target="_blank" rel="noopener" title="${{subName}}">
          <circle class="subspot-hit-circle" cx="${{px}}" cy="${{py}}" r="28" />
        </a>`;
      }}).join('');

      const groupsHtml = groups.map(g => {{
        const chipCls = g.highlight ? 'bird-chip highlight-chip' : 'bird-chip';
        const chips = g.items.map(item => `<span class="${{chipCls}}">${{item}}</span>`).join('');
        return `<div class="bird-group-row"><span class="bird-group-label">${{g.label}}:</span>${{chips}}</div>`;
      }}).join('');

      const qqNavUrl = `https://apis.map.qq.com/uri/v1/marker?marker=coord:${{spot.gcj_lat}},${{spot.gcj_lon}};title:${{encodeURIComponent(name)}};addr:${{encodeURIComponent('厦门市' + spot.district_zh)}}&referer=xmbirds`;
      const amapNavUrl = `https://uri.amap.com/marker?position=${{spot.gcj_lon}},${{spot.gcj_lat}}&name=${{encodeURIComponent(name)}}`;

      const sheet = document.getElementById('spotSheet');
      sheet.style.borderTopColor = c;
      sheet.innerHTML = `
        <div class="sheet-header">
          <div class="sheet-title-wrap">
            <span class="sheet-num" style="background:${{c}}">${{spot.id}}</span>
            <div>
              <h3 class="sheet-title">${{name}}</h3>
              <span style="font-size:12.5px;color:var(--ink-muted)">${{dist}} · ${{hab}}</span>
            </div>
          </div>
          <button class="close-btn" onclick="closeCard()" aria-label="Close">×</button>
        </div>

        <div class="meta-grid">
          <span class="meta-tag">${{t.labelDuration}}${{dur}}</span>
          <span class="meta-tag">${{t.labelMonths}}${{months}}</span>
        </div>

        <div class="local-map-box">
          <div class="local-map-header">
            <span>${{t.localMapTitle}}</span>
            <button class="zoom-img-btn" onclick="openLightbox('${{localImgSrc}}', '${{name.replace(/'/g, '')}}')">${{t.btnZoomLocal}}</button>
          </div>
          <div class="local-img-stage">
            <img class="local-spot-img" src="${{localImgSrc}}" alt="${{name}}" width="{LOCAL_IMG_W}" height="{LOCAL_IMG_H}" onclick="openLightbox('${{localImgSrc}}', '${{name.replace(/'/g, '')}}')" />
            <svg class="local-subspot-svg" viewBox="0 0 {LOCAL_IMG_W} {LOCAL_IMG_H}" xmlns="http://www.w3.org/2000/svg">
              ${{subspotsSvgHits}}
            </svg>
          </div>
          <div class="subspots-bar">
            <span style="font-size:12px;font-weight:700;color:var(--ink-muted)">${{t.subspotsNavLabel}}</span>
            ${{subspotsNavHtml}}
          </div>
        </div>

        <div class="sheet-desc">
          ${{descList.map(p => `<p>${{p}}</p>`).join('')}}
        </div>

        <div class="info-block"><strong>${{t.labelTransport}}</strong>${{transport}}</div>
        <div class="info-block"><strong>${{t.labelDifficulty}}</strong>${{diff}}</div>

        <div style="margin-top:10px">${{groupsHtml}}</div>

        <div class="sheet-tips"><strong>${{t.labelTip}}</strong>${{tips}}</div>

        <div class="sheet-actions">
          <a class="btn-primary" href="${{qqNavUrl}}" target="_blank" rel="noopener">${{t.btnTencent}}</a>
          <a class="btn-amap" href="${{amapNavUrl}}" target="_blank" rel="noopener">${{t.btnAmap}}</a>
        </div>
      `;

      document.getElementById('cardBackdrop').classList.add('open');
      sheet.classList.add('open');
    }}

    function closeCard() {{
      currentOpenSpotId = null;
      document.getElementById('cardBackdrop').classList.remove('open');
      document.getElementById('spotSheet').classList.remove('open');
    }}

    function setLanguage(lang) {{
      currentLang = lang;
      renderHeaderAndMap();
      renderTable();
      if (currentOpenSpotId !== null) {{
        selectSpot(currentOpenSpotId);
      }}
    }}

    renderHeaderAndMap();
    renderTable();
  </script>
</body>
</html>
'''


for fname, dlang in [("index4.html", "zh"), ("index4cn.html", "zh"), ("index4en.html", "en")]:
    out_p = os.path.join(OUT_DIR, fname)
    with open(out_p, "w", encoding="utf-8") as f:
        f.write(build_index4_page(dlang))
    print(f"Generated {out_p} ({os.path.getsize(out_p)} bytes, default={dlang})")
