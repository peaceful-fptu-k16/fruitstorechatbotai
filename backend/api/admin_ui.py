from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["admin-ui"])


ADMIN_HTML = """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Quản trị cửa hàng trái cây</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f3ea;
      --panel: #fffdf8;
      --panel-strong: #ffffff;
      --line: #e3dacb;
      --text: #1f2a24;
      --muted: #6e746e;
      --leaf: #24784e;
      --leaf-dark: #135b37;
      --lime: #dce875;
      --mango: #ffbd47;
      --orange: #f47a36;
      --berry: #c83f64;
      --sky: #cfe9ee;
      --danger: #b42318;
      --shadow: 0 18px 50px rgba(59, 42, 22, 0.13);
      --soft-shadow: 0 10px 28px rgba(59, 42, 22, 0.09);
    }

    * { box-sizing: border-box; }

    html {
      min-height: 100%;
      background: var(--bg);
    }

    body {
      min-height: 100vh;
      margin: 0;
      color: var(--text);
      font: 14px/1.45 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        linear-gradient(180deg, rgba(255, 250, 239, 0.95), rgba(247, 243, 234, 0.98)),
        repeating-linear-gradient(135deg, rgba(36, 120, 78, 0.045) 0 1px, transparent 1px 18px);
      overflow-x: hidden;
    }

    button, input, select, textarea {
      font: inherit;
    }

    button {
      border: 0;
      border-radius: 12px;
      background: var(--leaf);
      color: white;
      cursor: pointer;
      font-weight: 800;
      min-height: 40px;
      padding: 9px 14px;
      transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease;
      white-space: nowrap;
    }

    button:hover {
      box-shadow: 0 10px 22px rgba(36, 120, 78, 0.24);
      transform: translateY(-1px);
    }

    button:active {
      transform: translateY(0);
    }

    button:disabled {
      cursor: not-allowed;
      opacity: .55;
      transform: none;
      box-shadow: none;
    }

    button.secondary {
      background: #f4efe5;
      color: var(--text);
      border: 1px solid var(--line);
    }

    button.secondary:hover {
      box-shadow: var(--soft-shadow);
    }

    button.warning {
      background: var(--orange);
    }

    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      background: rgba(255, 255, 255, 0.92);
      color: var(--text);
      outline: none;
      transition: border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
    }

    input:focus, select:focus, textarea:focus {
      border-color: rgba(36, 120, 78, 0.55);
      box-shadow: 0 0 0 4px rgba(36, 120, 78, 0.12);
      background: white;
    }

    textarea {
      min-height: 94px;
      resize: vertical;
    }

    label {
      display: block;
      margin: 10px 0 6px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }

    h1, h2, h3, p { margin: 0; }

    .muted { color: var(--muted); }
    .money, .stock { font-variant-numeric: tabular-nums; font-weight: 900; }

    .status {
      min-height: 20px;
      margin-top: 10px;
      color: var(--muted);
      white-space: pre-wrap;
    }

    .status.error { color: var(--danger); }
    .status.ok { color: var(--leaf-dark); }

    .row {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .grid2 {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .view {
      min-height: 100vh;
      animation: viewIn 460ms ease both;
    }

    .hidden { display: none !important; }

    /* Login */
    .login-view {
      position: relative;
      display: grid;
      place-items: center;
      padding: 28px;
      overflow: hidden;
    }

    .fruit-sky {
      position: absolute;
      inset: 0;
      pointer-events: none;
      overflow: hidden;
    }

    .fruit-sky span {
      position: absolute;
      display: grid;
      place-items: center;
      width: 58px;
      height: 58px;
      border: 1px solid rgba(255, 255, 255, 0.75);
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.48);
      box-shadow: 0 12px 30px rgba(69, 48, 27, 0.09);
      font-size: 30px;
      animation: floatFruit var(--duration, 8s) ease-in-out infinite;
      opacity: 0.82;
    }

    .fruit-sky span:nth-child(1) { left: 7%; top: 13%; --duration: 8s; }
    .fruit-sky span:nth-child(2) { left: 82%; top: 10%; --duration: 9.5s; animation-delay: -2s; }
    .fruit-sky span:nth-child(3) { left: 12%; top: 76%; --duration: 10s; animation-delay: -4s; }
    .fruit-sky span:nth-child(4) { left: 86%; top: 71%; --duration: 8.6s; animation-delay: -1s; }
    .fruit-sky span:nth-child(5) { left: 50%; top: 7%; --duration: 11s; animation-delay: -5s; }
    .fruit-sky span:nth-child(6) { left: 38%; top: 83%; --duration: 9s; animation-delay: -3s; }

    .login-shell {
      position: relative;
      display: grid;
      width: min(980px, 100%);
      grid-template-columns: minmax(0, 1.05fr) 420px;
      gap: 0;
      overflow: hidden;
      border: 1px solid rgba(255, 255, 255, 0.8);
      border-radius: 28px;
      background: rgba(255, 253, 248, 0.82);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }

    .login-story {
      position: relative;
      min-height: 560px;
      padding: 42px;
      color: #163322;
      background:
        linear-gradient(140deg, rgba(220, 232, 117, 0.65), rgba(255, 189, 71, 0.52) 48%, rgba(207, 233, 238, 0.78));
      overflow: hidden;
    }

    .login-story::before {
      content: "";
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: 190px;
      background:
        linear-gradient(180deg, transparent, rgba(36, 120, 78, 0.16)),
        repeating-linear-gradient(90deg, rgba(36, 120, 78, 0.18) 0 6px, transparent 6px 18px);
      clip-path: polygon(0 34%, 9% 43%, 18% 28%, 30% 49%, 41% 24%, 53% 46%, 64% 30%, 77% 51%, 88% 28%, 100% 44%, 100% 100%, 0 100%);
    }

    .brand-mark {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.58);
      padding: 9px 12px;
      font-weight: 900;
      box-shadow: var(--soft-shadow);
    }

    .brand-mark span {
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: var(--leaf);
      color: white;
      animation: fruitPop 2.8s ease-in-out infinite;
    }

    .login-story h1 {
      position: relative;
      max-width: 520px;
      margin-top: 54px;
      font-size: clamp(36px, 5vw, 64px);
      line-height: 0.98;
      letter-spacing: 0;
    }

    .login-story p {
      position: relative;
      max-width: 440px;
      margin-top: 18px;
      color: rgba(31, 42, 36, 0.76);
      font-size: 16px;
      font-weight: 650;
    }

    .fruit-counter {
      position: absolute;
      left: 42px;
      bottom: 36px;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .fruit-counter div {
      min-width: 112px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.66);
      padding: 14px;
      box-shadow: var(--soft-shadow);
    }

    .fruit-counter strong {
      display: block;
      font-size: 22px;
      line-height: 1;
    }

    .fruit-counter small {
      color: var(--muted);
      font-weight: 800;
    }

    .login-panel {
      display: grid;
      align-content: center;
      padding: 42px;
      background: rgba(255, 253, 248, 0.92);
    }

    .login-panel h2 {
      font-size: 26px;
      letter-spacing: 0;
    }

    .login-panel .sub {
      margin-top: 8px;
      color: var(--muted);
      font-weight: 650;
    }

    .login-actions {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      margin-top: 18px;
    }

    /* Dashboard */
    .dashboard-view {
      display: grid;
      grid-template-rows: auto 1fr;
    }

    .topbar {
      position: sticky;
      top: 0;
      z-index: 20;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      border-bottom: 1px solid rgba(227, 218, 203, 0.82);
      background: rgba(255, 253, 248, 0.88);
      padding: 16px 24px;
      backdrop-filter: blur(16px);
    }

    .topbar-left {
      display: flex;
      align-items: center;
      min-width: 0;
      gap: 14px;
    }

    .logo {
      display: grid;
      place-items: center;
      width: 48px;
      height: 48px;
      flex: 0 0 auto;
      border-radius: 16px;
      background: linear-gradient(140deg, var(--leaf), var(--orange));
      color: white;
      font-size: 25px;
      box-shadow: 0 14px 28px rgba(36, 120, 78, 0.22);
      animation: fruitPop 3.2s ease-in-out infinite;
    }

    .topbar h1 {
      font-size: 21px;
      letter-spacing: 0;
    }

    .topbar p {
      color: var(--muted);
      font-weight: 650;
    }

    .harvest-strip {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 210px;
      overflow: hidden;
      border-radius: 999px;
      background: rgba(244, 239, 229, 0.85);
      padding: 8px 12px;
      box-shadow: inset 0 0 0 1px rgba(227, 218, 203, 0.8);
    }

    .harvest-strip span {
      display: inline-block;
      animation: parade 4.8s linear infinite;
      font-size: 20px;
    }

    .dashboard-shell {
      display: grid;
      grid-template-columns: 256px minmax(0, 1fr);
      gap: 22px;
      width: min(1480px, 100%);
      margin: 0 auto;
      padding: 24px;
    }

    .sidebar {
      align-self: start;
      position: sticky;
      top: 92px;
      display: grid;
      gap: 14px;
    }

    .nav-panel, .summary-panel, .tool-panel {
      border: 1px solid rgba(227, 218, 203, 0.9);
      border-radius: 22px;
      background: rgba(255, 253, 248, 0.86);
      box-shadow: var(--soft-shadow);
      backdrop-filter: blur(14px);
    }

    .nav-panel {
      padding: 12px;
    }

    .nav-btn {
      display: flex;
      align-items: center;
      width: 100%;
      gap: 10px;
      margin: 4px 0;
      background: transparent;
      color: var(--text);
      justify-content: flex-start;
      box-shadow: none;
    }

    .nav-btn:hover {
      background: rgba(36, 120, 78, 0.08);
      box-shadow: none;
    }

    .nav-btn.active {
      background: var(--leaf);
      color: white;
    }

    .summary-panel {
      padding: 16px;
    }

    .summary-panel h2, .tool-panel h2 {
      font-size: 15px;
      margin-bottom: 12px;
    }

    .metric {
      display: grid;
      grid-template-columns: 40px 1fr;
      gap: 10px;
      align-items: center;
      border-top: 1px solid var(--line);
      padding: 12px 0 0;
      margin-top: 12px;
    }

    .metric:first-of-type {
      border-top: 0;
      padding-top: 0;
      margin-top: 0;
    }

    .metric-icon {
      display: grid;
      place-items: center;
      width: 40px;
      height: 40px;
      border-radius: 14px;
      background: #f5ead1;
      font-size: 21px;
    }

    .metric strong {
      display: block;
      font-size: 22px;
      line-height: 1;
    }

    .metric span {
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }

    .content {
      min-width: 0;
    }

    .section {
      display: none;
      animation: sectionIn 340ms ease both;
    }

    .section.active {
      display: block;
    }

    .section-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 16px;
    }

    .section-head h2 {
      font-size: 28px;
      letter-spacing: 0;
    }

    .section-head p {
      color: var(--muted);
      font-weight: 650;
      margin-top: 4px;
    }

    .toolbar {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: min(430px, 100%);
    }

    .table-shell {
      overflow: hidden;
      border: 1px solid rgba(227, 218, 203, 0.94);
      border-radius: 24px;
      background: rgba(255, 253, 248, 0.9);
      box-shadow: var(--shadow);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      background: transparent;
    }

    th, td {
      border-bottom: 1px solid rgba(227, 218, 203, 0.85);
      padding: 14px 16px;
      text-align: left;
      vertical-align: middle;
    }

    th {
      color: var(--muted);
      background: rgba(244, 239, 229, 0.74);
      font-size: 12px;
      font-weight: 900;
      text-transform: uppercase;
    }

    tr {
      transition: background 160ms ease, transform 160ms ease;
    }

    tbody tr:hover td {
      background: rgba(36, 120, 78, 0.045);
    }

    tr.active td {
      background: rgba(220, 232, 117, 0.28);
    }

    tr:last-child td {
      border-bottom: 0;
    }

    .product-name {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 220px;
    }

    .fruit-avatar {
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      flex: 0 0 auto;
      border-radius: 16px;
      background: #f6ebd1;
      font-size: 22px;
      animation: gentleBob 3.8s ease-in-out infinite;
    }

    .product-actions {
      display: grid;
      grid-template-columns: 74px 78px 64px 64px;
      gap: 7px;
      align-items: center;
      min-width: 292px;
    }

    .editor-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 330px;
      gap: 18px;
    }

    .form-panel {
      border: 1px solid rgba(227, 218, 203, 0.94);
      border-radius: 24px;
      background: rgba(255, 253, 248, 0.92);
      box-shadow: var(--shadow);
      padding: 20px;
    }

    .editor-empty {
      display: grid;
      min-height: 460px;
      place-items: center;
      text-align: center;
      border: 1px dashed rgba(36, 120, 78, 0.35);
      border-radius: 24px;
      background:
        linear-gradient(140deg, rgba(220, 232, 117, 0.24), rgba(207, 233, 238, 0.32)),
        rgba(255, 253, 248, 0.72);
    }

    .editor-empty .big-fruit {
      font-size: 76px;
      animation: fruitPop 3s ease-in-out infinite;
    }

    .selected-preview {
      display: grid;
      gap: 12px;
    }

    .preview-card {
      border-radius: 24px;
      background: linear-gradient(145deg, rgba(36, 120, 78, 0.95), rgba(244, 122, 54, 0.9));
      color: white;
      padding: 20px;
      overflow: hidden;
      box-shadow: var(--shadow);
    }

    .preview-card .emoji {
      display: block;
      margin-bottom: 18px;
      font-size: 64px;
      animation: gentleBob 3.5s ease-in-out infinite;
    }

    .preview-card strong {
      display: block;
      font-size: 22px;
      line-height: 1.15;
    }

    .taste-list {
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }

    .taste-row {
      display: grid;
      gap: 5px;
    }

    .taste-row span {
      display: flex;
      justify-content: space-between;
      color: var(--muted);
      font-size: 12px;
      font-weight: 900;
    }

    .bar {
      height: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: #efe7d9;
    }

    .bar i {
      display: block;
      height: 100%;
      width: var(--value, 50%);
      border-radius: inherit;
      background: linear-gradient(90deg, var(--leaf), var(--mango));
      animation: fillBar 650ms ease both;
    }

    .audit-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .audit-item {
      position: relative;
      overflow: hidden;
      border: 1px solid rgba(227, 218, 203, 0.94);
      border-radius: 20px;
      background: rgba(255, 253, 248, 0.92);
      padding: 16px;
      box-shadow: var(--soft-shadow);
      animation: sectionIn 320ms ease both;
    }

    .audit-item::before {
      content: "";
      position: absolute;
      inset: 0 auto 0 0;
      width: 5px;
      background: linear-gradient(180deg, var(--leaf), var(--mango), var(--berry));
    }

    .audit-item strong {
      display: block;
      font-size: 16px;
      margin-bottom: 6px;
    }

    .audit-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      background: #f4efe5;
      color: var(--text);
      padding: 5px 9px;
      font-size: 12px;
      font-weight: 850;
    }

    @keyframes viewIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes sectionIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @keyframes floatFruit {
      0%, 100% { transform: translate3d(0, 0, 0) rotate(0deg); }
      40% { transform: translate3d(18px, -20px, 0) rotate(7deg); }
      70% { transform: translate3d(-10px, 12px, 0) rotate(-5deg); }
    }

    @keyframes fruitPop {
      0%, 100% { transform: scale(1) rotate(0deg); }
      45% { transform: scale(1.08) rotate(-3deg); }
      70% { transform: scale(0.98) rotate(2deg); }
    }

    @keyframes gentleBob {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-5px); }
    }

    @keyframes parade {
      0% { transform: translateX(0) rotate(0deg); }
      100% { transform: translateX(-42px) rotate(360deg); }
    }

    @keyframes fillBar {
      from { width: 0; }
      to { width: var(--value, 50%); }
    }

    @media (max-width: 1120px) {
      .dashboard-shell {
        grid-template-columns: 1fr;
      }

      .sidebar {
        position: static;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      }

      .nav-panel {
        display: flex;
        gap: 8px;
        overflow-x: auto;
      }

      .nav-btn {
        width: auto;
      }

      .editor-grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 860px) {
      .login-shell {
        grid-template-columns: 1fr;
      }

      .login-story {
        min-height: 380px;
      }

      .fruit-counter {
        position: relative;
        left: auto;
        bottom: auto;
        margin-top: 24px;
      }

      .topbar {
        align-items: flex-start;
        flex-direction: column;
      }

      .harvest-strip {
        width: 100%;
      }

      .section-head {
        flex-direction: column;
      }

      .toolbar {
        width: 100%;
        min-width: 0;
      }

      .audit-grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 680px) {
      .login-view, .dashboard-shell {
        padding: 14px;
      }

      .login-story, .login-panel {
        padding: 24px;
      }

      .login-story h1 {
        font-size: 38px;
      }

      .sidebar {
        grid-template-columns: 1fr;
      }

      .grid2 {
        grid-template-columns: 1fr;
      }

      .table-shell {
        overflow-x: auto;
      }

      table {
        min-width: 860px;
      }
    }
  </style>
</head>
<body>
  <section id="loginView" class="view login-view">
    <div class="fruit-sky" aria-hidden="true">
      <span>🍊</span>
      <span>🍇</span>
      <span>🍓</span>
      <span>🥝</span>
      <span>🍍</span>
      <span>🥭</span>
    </div>

    <div class="login-shell">
      <div class="login-story">
        <div class="brand-mark"><span>🍃</span> Vườn Trái Cây Tươi</div>
        <h1>Quản trị gian hàng trái cây</h1>
        <p>Theo dõi tồn kho, chỉnh giá và cập nhật mô tả sản phẩm để chatbot tư vấn đúng thông tin mới nhất.</p>
        <div class="fruit-counter">
          <div><strong id="loginProductCount">--</strong><small>Sản phẩm</small></div>
          <div><strong id="loginStockCount">--</strong><small>Tổng tồn kho</small></div>
        </div>
      </div>

      <form id="loginForm" class="login-panel">
        <h2>Đăng nhập quản trị</h2>
        <p class="sub">Dành riêng cho nhân viên cập nhật sản phẩm và tồn kho.</p>
        <label for="username">Tên đăng nhập</label>
        <input id="username" autocomplete="username" value="admin" />
        <label for="password">Mật khẩu</label>
        <input id="password" type="password" autocomplete="current-password" />
        <div class="login-actions">
          <button type="submit">Vào bảng điều khiển</button>
          <button id="clearTokenBtn" class="secondary" type="button">Xóa phiên</button>
        </div>
        <div id="authStatus" class="status"></div>
      </form>
    </div>
  </section>

  <section id="dashboardView" class="view dashboard-view hidden">
    <header class="topbar">
      <div class="topbar-left">
        <div class="logo">🍊</div>
        <div>
          <h1>Bảng điều khiển cửa hàng trái cây</h1>
          <p id="welcomeText">Đã đăng nhập</p>
        </div>
      </div>
      <div class="row">
        <div class="harvest-strip" aria-hidden="true">
          <span>🍎</span><span>🍋</span><span>🍉</span><span>🍇</span><span>🥭</span><span>🍓</span><span>🍍</span>
        </div>
        <button id="logoutBtn" class="secondary" type="button">Đăng xuất</button>
      </div>
    </header>

    <div class="dashboard-shell">
      <aside class="sidebar">
        <nav class="nav-panel" aria-label="Điều hướng quản trị">
          <button class="nav-btn active" type="button" data-section="productsSection">🍇 Sản phẩm</button>
          <button class="nav-btn" type="button" data-section="editorSection">🥭 Chi tiết</button>
          <button class="nav-btn" type="button" data-section="auditSection">🍃 Lịch sử</button>
        </nav>

        <section class="summary-panel">
          <h2>Tổng quan hôm nay</h2>
          <div class="metric">
            <div class="metric-icon">🍊</div>
            <div><strong id="metricProducts">0</strong><span>Sản phẩm đang quản lý</span></div>
          </div>
          <div class="metric">
            <div class="metric-icon">📦</div>
            <div><strong id="metricStock">0</strong><span>Tổng tồn kho</span></div>
          </div>
          <div class="metric">
            <div class="metric-icon">✨</div>
            <div><strong id="metricAvailable">0</strong><span>Mặt hàng còn bán</span></div>
          </div>
        </section>
      </aside>

      <main class="content">
        <section id="productsSection" class="section active">
          <div class="section-head">
            <div>
              <h2>Sản phẩm và tồn kho</h2>
              <p>Cập nhật số lượng nhanh, hoặc chọn “Sửa” để mở phần chi tiết.</p>
            </div>
            <div class="toolbar">
              <input id="search" placeholder="Tìm theo tên trái cây" />
              <button id="refreshBtn" class="secondary" type="button">Tải lại</button>
            </div>
          </div>

          <div class="table-shell">
            <table>
              <thead>
                <tr>
                  <th style="width:70px;">Mã</th>
                  <th>Sản phẩm</th>
                  <th style="width:125px;">Giá</th>
                  <th style="width:95px;">Tồn</th>
                  <th style="width:310px;">Thao tác</th>
                </tr>
              </thead>
              <tbody id="productsBody"></tbody>
            </table>
          </div>
          <div id="stockStatus" class="status"></div>
        </section>

        <section id="editorSection" class="section">
          <div class="section-head">
            <div>
              <h2>Chi tiết sản phẩm</h2>
              <p>Sửa thông tin mà chatbot dùng để tư vấn cho khách.</p>
            </div>
            <button id="backToProductsBtn" class="secondary" type="button">Quay lại sản phẩm</button>
          </div>

          <div id="editorEmpty" class="editor-empty">
            <div>
              <div class="big-fruit">🥭</div>
              <h2>Chưa chọn sản phẩm</h2>
              <p class="muted">Chọn một sản phẩm trong danh sách để bắt đầu chỉnh sửa.</p>
            </div>
          </div>

          <div id="editorWrap" class="editor-grid hidden">
            <form id="productForm" class="form-panel">
              <div class="grid2">
                <div>
                  <label for="editName">Tên sản phẩm</label>
                  <input id="editName" />
                </div>
                <div>
                  <label for="editPrice">Giá bán</label>
                  <input id="editPrice" type="number" min="0" />
                </div>
              </div>
              <div class="grid2">
                <div>
                  <label for="editOrigin">Nguồn gốc</label>
                  <input id="editOrigin" />
                </div>
                <div>
                  <label for="editSeason">Mùa vụ</label>
                  <input id="editSeason" />
                </div>
              </div>
              <div class="grid2">
                <div>
                  <label for="editSweet">Độ ngọt 0-10</label>
                  <input id="editSweet" type="number" min="0" max="10" />
                </div>
                <div>
                  <label for="editSour">Độ chua 0-10</label>
                  <input id="editSour" type="number" min="0" max="10" />
                </div>
              </div>
              <div class="grid2">
                <div>
                  <label for="editJuicy">Độ mọng nước 0-10</label>
                  <input id="editJuicy" type="number" min="0" max="10" />
                </div>
                <div>
                  <label for="editAroma">Độ thơm 0-10</label>
                  <input id="editAroma" type="number" min="0" max="10" />
                </div>
              </div>
              <label for="editBestUse">Gợi ý sử dụng</label>
              <input id="editBestUse" />
              <label for="editDescription">Mô tả sản phẩm</label>
              <textarea id="editDescription"></textarea>
              <div class="row" style="margin-top: 14px;">
                <button type="submit">Lưu thay đổi</button>
                <button id="clearEditorBtn" class="secondary" type="button">Bỏ chọn</button>
              </div>
              <div id="editStatus" class="status"></div>
            </form>

            <aside class="selected-preview">
              <div class="preview-card">
                <span id="previewEmoji" class="emoji">🍊</span>
                <strong id="previewName">Sản phẩm</strong>
                <p id="previewMeta">Nguồn gốc và mùa vụ</p>
              </div>
              <div class="form-panel">
                <h2>Hồ sơ hương vị</h2>
                <div class="taste-list">
                  <div class="taste-row"><span><b>Ngọt</b><b id="sweetValue">0/10</b></span><div class="bar"><i id="sweetBar"></i></div></div>
                  <div class="taste-row"><span><b>Chua</b><b id="sourValue">0/10</b></span><div class="bar"><i id="sourBar"></i></div></div>
                  <div class="taste-row"><span><b>Mọng nước</b><b id="juicyValue">0/10</b></span><div class="bar"><i id="juicyBar"></i></div></div>
                  <div class="taste-row"><span><b>Thơm</b><b id="aromaValue">0/10</b></span><div class="bar"><i id="aromaBar"></i></div></div>
                </div>
              </div>
            </aside>
          </div>
        </section>

        <section id="auditSection" class="section">
          <div class="section-head">
            <div>
              <h2>Lịch sử cập nhật</h2>
              <p>Theo dõi thao tác thay đổi tồn kho và thông tin sản phẩm.</p>
            </div>
            <button id="auditBtn" class="secondary" type="button">Tải lại lịch sử</button>
          </div>
          <div id="auditList" class="audit-grid"></div>
          <div id="auditStatus" class="status"></div>
        </section>
      </main>
    </div>
  </section>

  <script>
    const tokenKey = "fruitstore_admin_token";
    const loginView = document.querySelector("#loginView");
    const dashboardView = document.querySelector("#dashboardView");
    const productsBody = document.querySelector("#productsBody");
    const authStatus = document.querySelector("#authStatus");
    const stockStatus = document.querySelector("#stockStatus");
    const editStatus = document.querySelector("#editStatus");
    const auditStatus = document.querySelector("#auditStatus");
    const auditList = document.querySelector("#auditList");
    const searchInput = document.querySelector("#search");
    const editorEmpty = document.querySelector("#editorEmpty");
    const editorWrap = document.querySelector("#editorWrap");
    let products = [];
    let selectedProductId = null;

    const fields = {
      name: document.querySelector("#editName"),
      price: document.querySelector("#editPrice"),
      origin: document.querySelector("#editOrigin"),
      season: document.querySelector("#editSeason"),
      sweetness_level: document.querySelector("#editSweet"),
      sourness_level: document.querySelector("#editSour"),
      juiciness_level: document.querySelector("#editJuicy"),
      aroma_level: document.querySelector("#editAroma"),
      best_use: document.querySelector("#editBestUse"),
      description: document.querySelector("#editDescription"),
    };

    const fruitEmojiMap = [
      ["xoài", "🥭"], ["cam", "🍊"], ["nho", "🍇"], ["bưởi", "🍊"], ["táo", "🍎"],
      ["dâu", "🍓"], ["kiwi", "🥝"], ["lê", "🍐"], ["dứa", "🍍"], ["chuối", "🍌"],
      ["việt quất", "🫐"], ["thanh long", "🐉"], ["mận", "🟣"], ["ổi", "🍈"]
    ];

    function normalizeText(value) {
      return value.toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").replace(/đ/g, "d");
    }

    function fruitEmoji(name) {
      const normalized = normalizeText(name);
      for (const [key, emoji] of fruitEmojiMap) {
        if (normalized.includes(normalizeText(key))) return emoji;
      }
      return "🍏";
    }

    function formatVnd(value) {
      return new Intl.NumberFormat("vi-VN").format(value) + "đ";
    }

    function formatNumber(value) {
      return new Intl.NumberFormat("vi-VN").format(value);
    }

    function token() {
      return localStorage.getItem(tokenKey) || "";
    }

    function setStatus(node, text, type = "") {
      node.textContent = text;
      node.classList.toggle("error", type === "error");
      node.classList.toggle("ok", type === "ok");
    }

    function showLogin() {
      loginView.classList.remove("hidden");
      dashboardView.classList.add("hidden");
    }

    function showDashboard() {
      loginView.classList.add("hidden");
      dashboardView.classList.remove("hidden");
    }

    function switchSection(sectionId) {
      document.querySelectorAll(".section").forEach((section) => {
        section.classList.toggle("active", section.id === sectionId);
      });
      document.querySelectorAll(".nav-btn").forEach((button) => {
        button.classList.toggle("active", button.dataset.section === sectionId);
      });
    }

    async function requestJson(path, options = {}) {
      const response = await fetch(path, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
      });
      const text = await response.text();
      const payload = text ? JSON.parse(text) : {};
      if (!response.ok) {
        throw new Error(payload.detail || text || `Yêu cầu thất bại: ${response.status}`);
      }
      return payload;
    }

    function authHeaders(extra = {}) {
      return {
        Authorization: `Bearer ${token()}`,
        ...extra,
      };
    }

    function updateMetrics() {
      const totalProducts = products.length;
      const totalStock = products.reduce((sum, item) => sum + Number(item.stock || 0), 0);
      const available = products.filter((item) => item.stock > 0).length;
      document.querySelector("#metricProducts").textContent = formatNumber(totalProducts);
      document.querySelector("#metricStock").textContent = formatNumber(totalStock);
      document.querySelector("#metricAvailable").textContent = formatNumber(available);
      document.querySelector("#loginProductCount").textContent = formatNumber(totalProducts);
      document.querySelector("#loginStockCount").textContent = formatNumber(totalStock);
    }

    async function login(event) {
      event.preventDefault();
      setStatus(authStatus, "Đang đăng nhập...");
      try {
        const payload = await requestJson("/admin/login", {
          method: "POST",
          body: JSON.stringify({
            username: document.querySelector("#username").value,
            password: document.querySelector("#password").value,
          }),
        });
        localStorage.setItem(tokenKey, payload.access_token);
        setStatus(authStatus, `Đăng nhập thành công. Phiên hết hạn sau ${payload.expires_in_minutes} phút.`, "ok");
        showDashboard();
        await Promise.all([loadProducts(), loadAudit()]);
      } catch (error) {
        setStatus(authStatus, error.message, "error");
      }
    }

    function selectProduct(productId) {
      selectedProductId = Number(productId);
      const product = products.find((item) => item.id === selectedProductId);
      if (!product) return;

      editorEmpty.classList.add("hidden");
      editorWrap.classList.remove("hidden");
      fields.name.value = product.name;
      fields.price.value = product.price;
      fields.origin.value = product.origin;
      fields.season.value = product.season;
      fields.sweetness_level.value = product.sweetness_level;
      fields.sourness_level.value = product.sourness_level;
      fields.juiciness_level.value = product.juiciness_level;
      fields.aroma_level.value = product.aroma_level;
      fields.best_use.value = product.best_use;
      fields.description.value = product.description;
      setStatus(editStatus, "");
      updatePreview();
      renderProducts();
      switchSection("editorSection");
    }

    function clearEditor() {
      selectedProductId = null;
      editorWrap.classList.add("hidden");
      editorEmpty.classList.remove("hidden");
      setStatus(editStatus, "");
      renderProducts();
    }

    function setBar(id, value) {
      const percent = Math.max(0, Math.min(10, Number(value || 0))) * 10;
      document.querySelector(`#${id}`).style.setProperty("--value", `${percent}%`);
    }

    function updatePreview() {
      const product = products.find((item) => item.id === selectedProductId);
      if (!product) return;
      document.querySelector("#previewEmoji").textContent = fruitEmoji(product.name);
      document.querySelector("#previewName").textContent = product.name;
      document.querySelector("#previewMeta").textContent = `${product.origin || "Chưa có nguồn gốc"} · ${product.season || "Chưa có mùa vụ"}`;
      document.querySelector("#sweetValue").textContent = `${product.sweetness_level}/10`;
      document.querySelector("#sourValue").textContent = `${product.sourness_level}/10`;
      document.querySelector("#juicyValue").textContent = `${product.juiciness_level}/10`;
      document.querySelector("#aromaValue").textContent = `${product.aroma_level}/10`;
      setBar("sweetBar", product.sweetness_level);
      setBar("sourBar", product.sourness_level);
      setBar("juicyBar", product.juiciness_level);
      setBar("aromaBar", product.aroma_level);
    }

    function renderProducts() {
      productsBody.innerHTML = "";
      for (const product of products) {
        const row = document.createElement("tr");
        if (product.id === selectedProductId) row.classList.add("active");
        row.innerHTML = `
          <td>${product.id}</td>
          <td>
            <div class="product-name">
              <div class="fruit-avatar">${fruitEmoji(product.name)}</div>
              <div>
                <strong>${product.name}</strong>
                <div class="muted">${product.origin || ""} ${product.season ? "· " + product.season : ""}</div>
              </div>
            </div>
          </td>
          <td class="money">${formatVnd(product.price)}</td>
          <td class="stock" data-stock-id="${product.id}">${product.stock}</td>
          <td>
            <div class="product-actions">
              <select data-operation="${product.id}">
                <option value="set">Đặt</option>
                <option value="inc">Tăng</option>
                <option value="dec">Giảm</option>
              </select>
              <input type="number" min="0" value="${product.stock}" data-quantity="${product.id}" />
              <button type="button" data-update="${product.id}">Lưu</button>
              <button class="secondary" type="button" data-edit="${product.id}">Sửa</button>
            </div>
          </td>
        `;
        productsBody.appendChild(row);
      }
      updateMetrics();
    }

    async function loadProducts() {
      setStatus(stockStatus, "Đang tải sản phẩm...");
      try {
        const query = searchInput.value.trim();
        const params = new URLSearchParams({ limit: "200" });
        if (query) params.set("query", query);
        const payload = await requestJson(`/products?${params.toString()}`);
        products = payload.items;
        renderProducts();
        if (selectedProductId) updatePreview();
        setStatus(stockStatus, `Đã tải ${payload.items.length} sản phẩm.`, "ok");
      } catch (error) {
        setStatus(stockStatus, error.message, "error");
      }
    }

    async function updateStock(productId) {
      if (!token()) {
        setStatus(stockStatus, "Bạn cần đăng nhập quản trị trước.", "error");
        showLogin();
        return;
      }
      const operation = document.querySelector(`[data-operation="${productId}"]`).value;
      const quantity = Number(document.querySelector(`[data-quantity="${productId}"]`).value || 0);
      setStatus(stockStatus, "Đang cập nhật tồn kho...");
      try {
        const payload = await requestJson("/admin/update-stock", {
          method: "POST",
          headers: authHeaders({ "Idempotency-Key": `stock-${productId}-${Date.now()}` }),
          body: JSON.stringify({
            updates: [{ product_id: Number(productId), operation, quantity }],
          }),
        });
        for (const item of payload.updates) {
          const product = products.find((entry) => entry.id === item.product_id);
          if (product) product.stock = item.stock;
        }
        renderProducts();
        await loadAudit();
        setStatus(stockStatus, `Đã cập nhật ${payload.updates.length} sản phẩm.`, "ok");
      } catch (error) {
        setStatus(stockStatus, error.message, "error");
      }
    }

    async function saveProduct(event) {
      event.preventDefault();
      if (!selectedProductId) return;
      if (!token()) {
        setStatus(editStatus, "Bạn cần đăng nhập quản trị trước.", "error");
        showLogin();
        return;
      }

      const payload = {
        name: fields.name.value.trim(),
        price: Number(fields.price.value || 0),
        origin: fields.origin.value.trim(),
        season: fields.season.value.trim(),
        sweetness_level: Number(fields.sweetness_level.value || 0),
        sourness_level: Number(fields.sourness_level.value || 0),
        juiciness_level: Number(fields.juiciness_level.value || 0),
        aroma_level: Number(fields.aroma_level.value || 0),
        best_use: fields.best_use.value.trim(),
        description: fields.description.value.trim(),
      };

      setStatus(editStatus, "Đang lưu thông tin sản phẩm...");
      try {
        const response = await requestJson(`/admin/products/${selectedProductId}`, {
          method: "PATCH",
          headers: authHeaders(),
          body: JSON.stringify(payload),
        });
        const index = products.findIndex((item) => item.id === response.product.id);
        if (index >= 0) products[index] = response.product;
        renderProducts();
        updatePreview();
        await loadAudit();
        const message = response.changed_fields.length
          ? `Đã lưu: ${response.changed_fields.join(", ")}`
          : "Không có thay đổi mới.";
        setStatus(editStatus, message, "ok");
      } catch (error) {
        setStatus(editStatus, error.message, "error");
      }
    }

    function operationText(operation) {
      if (operation === "set") return "Đặt tồn kho";
      if (operation === "inc") return "Tăng tồn kho";
      if (operation === "dec") return "Giảm tồn kho";
      if (operation === "product_update") return "Sửa thông tin";
      return operation;
    }

    async function loadAudit() {
      if (!token()) {
        auditList.innerHTML = "";
        setStatus(auditStatus, "Đăng nhập để xem lịch sử cập nhật.");
        return;
      }
      setStatus(auditStatus, "Đang tải lịch sử...");
      try {
        const payload = await requestJson("/admin/inventory-events?limit=24", {
          headers: authHeaders(),
        });
        auditList.innerHTML = "";
        for (const item of payload.items) {
          const node = document.createElement("article");
          node.className = "audit-item";
          node.innerHTML = `
            <strong>${fruitEmoji(item.product_name)} ${item.product_name || "Sản phẩm #" + item.product_id}</strong>
            <div>${operationText(item.operation)}</div>
            <div class="audit-meta">
              <span class="pill">Delta ${item.quantity_delta}</span>
              <span class="pill">Tồn ${item.new_stock}</span>
              <span class="pill">${item.actor}</span>
            </div>
            <p class="muted" style="margin-top: 10px;">${new Date(item.created_at).toLocaleString("vi-VN")}</p>
          `;
          auditList.appendChild(node);
        }
        setStatus(auditStatus, payload.items.length ? `Đã tải ${payload.items.length} mục lịch sử.` : "Chưa có lịch sử cập nhật.", "ok");
      } catch (error) {
        setStatus(auditStatus, error.message, "error");
      }
    }

    document.querySelector("#loginForm").addEventListener("submit", login);
    document.querySelector("#clearTokenBtn").addEventListener("click", () => {
      localStorage.removeItem(tokenKey);
      setStatus(authStatus, "Đã xóa phiên đăng nhập.", "ok");
      showLogin();
    });
    document.querySelector("#logoutBtn").addEventListener("click", () => {
      localStorage.removeItem(tokenKey);
      clearEditor();
      showLogin();
      setStatus(authStatus, "Bạn đã đăng xuất.", "ok");
    });
    document.querySelector("#refreshBtn").addEventListener("click", loadProducts);
    document.querySelector("#productForm").addEventListener("submit", saveProduct);
    document.querySelector("#clearEditorBtn").addEventListener("click", clearEditor);
    document.querySelector("#auditBtn").addEventListener("click", loadAudit);
    document.querySelector("#backToProductsBtn").addEventListener("click", () => switchSection("productsSection"));
    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") loadProducts();
    });
    productsBody.addEventListener("click", (event) => {
      const updateButton = event.target.closest("[data-update]");
      if (updateButton) updateStock(updateButton.dataset.update);
      const editButton = event.target.closest("[data-edit]");
      if (editButton) selectProduct(editButton.dataset.edit);
    });
    document.querySelectorAll(".nav-btn").forEach((button) => {
      button.addEventListener("click", () => switchSection(button.dataset.section));
    });

    async function bootstrap() {
      try {
        await loadProducts();
      } catch {
        updateMetrics();
      }
      if (token()) {
        showDashboard();
        await loadAudit();
      } else {
        showLogin();
      }
    }

    bootstrap();
  </script>
</body>
</html>
"""


@router.get("/admin", response_class=HTMLResponse)
def admin_home() -> HTMLResponse:
    return HTMLResponse(ADMIN_HTML)
