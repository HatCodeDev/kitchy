from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


_RESET_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Reset your Kitchy password</title>
  <style>
    :root { color-scheme: light dark; }
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: #f4f5f7; color: #1a1a1a; padding: 16px;
    }
    .card {
      width: 100%; max-width: 380px; background: #fff; border-radius: 14px;
      padding: 32px 28px; box-shadow: 0 8px 30px rgba(0,0,0,.08);
    }
    h1 { margin: 0 0 4px; font-size: 22px; }
    h2 { margin: 0 0 20px; font-size: 15px; font-weight: 500; color: #666; }
    label { display: block; font-size: 13px; margin: 12px 0 6px; color: #444; }
    input {
      width: 100%; padding: 11px 12px; border: 1px solid #d0d3d9; border-radius: 8px;
      font-size: 15px; outline: none;
    }
    input:focus { border-color: #4a7dff; }
    button {
      width: 100%; margin-top: 20px; padding: 12px; border: 0; border-radius: 8px;
      background: #4a7dff; color: #fff; font-size: 15px; font-weight: 600; cursor: pointer;
    }
    button:disabled { opacity: .6; cursor: default; }
    #msg { margin: 16px 0 0; font-size: 14px; min-height: 18px; }
    #msg.ok { color: #1a7f37; }
    #msg.err { color: #c1392b; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Kitchy</h1>
    <h2>Set a new password</h2>
    <form id="form">
      <label for="pw">New password</label>
      <input type="password" id="pw" minlength="8" required autocomplete="new-password">
      <label for="pw2">Confirm password</label>
      <input type="password" id="pw2" minlength="8" required autocomplete="new-password">
      <button type="submit">Update password</button>
    </form>
    <p id="msg"></p>
  </div>
  <script>
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const form = document.getElementById("form");
    const msg = document.getElementById("msg");

    function show(text, ok) {
      msg.textContent = text;
      msg.className = ok ? "ok" : "err";
    }

    if (!token) {
      form.style.display = "none";
      show("Invalid or missing reset link.", false);
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const pw = document.getElementById("pw").value;
      const pw2 = document.getElementById("pw2").value;
      if (pw.length < 8) { show("Password must be at least 8 characters.", false); return; }
      if (pw !== pw2) { show("Passwords do not match.", false); return; }

      const btn = form.querySelector("button");
      btn.disabled = true;
      show("", true);
      try {
        const res = await fetch("/api/v1/auth/reset-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: token, new_password: pw })
        });
        if (res.ok) {
          form.style.display = "none";
          show("Password updated. You can now log in with your new password.", true);
        } else if (res.status === 429) {
          show("Too many attempts. Please wait a minute and try again.", false);
          btn.disabled = false;
        } else {
          const data = await res.json().catch(() => ({}));
          show(data.detail || "Invalid or expired reset link.", false);
          btn.disabled = false;
        }
      } catch (err) {
        show("Network error. Please try again.", false);
        btn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@router.get("/reset-password", response_class=HTMLResponse, include_in_schema=False)
async def reset_password_page() -> HTMLResponse:
    """Serves the password-reset form that the emailed link points to.
    The token is read client-side from the URL and submitted to
    POST /api/v1/auth/reset-password."""
    return HTMLResponse(content=_RESET_PAGE)
