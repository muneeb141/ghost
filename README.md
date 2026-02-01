# 👻 Ghost

**Let users browse anonymously, convert them when they're ready.**

Stop losing customers at the signup wall. Ghost turns anonymous visitors into authenticated users without breaking their flow.

```bash
# Install
bench get-app https://github.com/muneeb141/ghost
bench --site your-site install-app ghost
```

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Frappe](https://img.shields.io/badge/Frappe-v15+-orange.svg)](https://frappeframework.com)

---

## ⚡ Quick Start

1. **Create OAuth Client** → Setup > Integrations > OAuth Client
2. **Enable Ghost** → Setup > Ghost Settings → Paste Client ID
3. **Done!** Test with curl:

```bash
curl -X POST http://your-site:8000/api/method/ghost.api.ghost.create_ghost_session
```

**What you get back:**
```json
{
  "user": "ghost_abc123@guest.local",
  "access_token": "...",    // Use this to make authenticated requests
  "refresh_token": "...",   // Use this to get new access tokens
  "expires_in": 3600        // Token valid for 1 hour
}
```

---

## 🎯 What Problem Does This Solve?

**Before Ghost:**
- User visits your site → Signup wall → 70% bounce
- Mobile app → Complex login flow → User drops off
- E-commerce → "Add to cart" requires account → Lost sale

**After Ghost:**
1. User arrives → Gets temporary "ghost" identity instantly
2. Browses, adds to cart, saves favorites → All tracked
3. Ready to checkout → Quick OTP → Becomes real user
4. **All data preserved!** Cart, favorites, browsing history

**Perfect for:**
- 🛒 E-commerce (browse → cart → checkout → sign up)
- 📱 Mobile apps (explore → authenticate when needed)
- 📰 Content platforms (read → save → register)
- 💼 SaaS (try features → upgrade → convert)

---

## 🚀 How It Works

```
Anonymous User
      ↓
Create Ghost Session  →  Get Bearer Token
      ↓
Browse, Add to Cart   →  Authenticated as ghost_abc123@guest.local
      ↓
Ready to Convert      →  Send OTP to email
      ↓
Enter OTP             →  Convert to user@example.com
      ↓
All cart data stays!  →  New tokens for real user
```

**Under the hood:**
- OAuth2 bearer tokens (industry standard, super secure)
- No cookies needed (perfect for mobile/SPAs)
- Tokens expire & refresh automatically
- All ghost data merges into real user on conversion

---

## 📱 Frontend Integration (Copy-Paste Ready)

### JavaScript/React/Vue

```javascript
// 1. Create ghost on page load
const response = await fetch('/api/method/ghost.api.ghost.create_ghost_session', {
  method: 'POST'
});
const { access_token, refresh_token } = await response.json().message;
sessionStorage.setItem('token', access_token);

// 2. Make authenticated requests
fetch('/api/resource/Item', {
  headers: { 'Authorization': `Bearer ${sessionStorage.getItem('token')}` }
});

// 3. Convert when ready
// Send OTP
await fetch('/api/method/ghost.api.otp.send_otp', {
  method: 'POST',
  body: JSON.stringify({ email: 'user@example.com', purpose: 'Conversion' })
});

// Convert with OTP
await fetch('/api/method/ghost.api.ghost.convert_to_real_user', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    ghost_email: 'ghost_xxx@guest.local',
    real_email: 'user@example.com',
    otp_code: '123456'
  })
});
// ✨ User converted! All data preserved!
```

---

## 🎮 Test It Out

We've included a **Bruno collection** with ready-to-run API tests:

```bash
# Open apps/ghost/bruno/ in Bruno
# Run tests in order:
1. Create Ghost Session  ✓
2. Refresh Token         ✓
3. Send OTP              ✓
4. Convert to Real User  ✓
```

[Full testing guide →](bruno/README.md)

---

## ⚙️ Configuration (The Important Bits)

**Ghost Settings** (Setup > Ghost Settings):

| Setting | What It Does | Default |
|---------|--------------|---------|
| **Client ID** | OAuth client (required!) | - |
| Access Token Expiry | How long before re-auth | 1 hour |
| Invalidate on Conversion | Revoke ghost tokens when converting | ✓ |
| Verify OTP on Conversion | Require email verification | ✓ |

**That's it!** Everything else has smart defaults.

---

## 🔐 Security (Yes, It's Production-Ready)

✅ **OAuth2 bearer tokens** (same as Google/Facebook)  
✅ **Short-lived access tokens** (1 hour, configurable)  
✅ **Token refresh** without re-login  
✅ **Automatic token revocation** on conversion  
✅ **Rate limiting** on all endpoints  
✅ **HTTPS support** (required in production)

**Mobile apps?** Works perfectly (no cookies needed).

---

## 📚 Full Documentation

**Too much info above?** → [Full README →](docs/FULL_README.md)  
**Need API reference?** → [Bruno tests →](bruno/README.md)  
**Want examples?** → See Frontend Integration above ↑

---

## 🤔 Common Questions

**Q: Do I need to handle token refresh myself?**  
A: Yes, but it's one API call. Just call `/refresh_bearer_token` before expiry.

**Q: What happens to ghost user's cart when they convert?**  
A: Everything moves to their real account. Documents, cart items, favorites—all transferred.

**Q: Can I use this in production?**  
A: Yes! OAuth2 tokens are industry-standard. Used in real ecommerce sites.

**Q: Mobile app support?**  
A: Perfect for mobile. No cookies, just tokens. Works on iOS/Android.

**Q: Is it GDPR compliant?**  
A: Yes. Ghost users auto-delete after expiry. Full data control.

---

## 🛠️ Troubleshooting

**"OAuth Client ID is required"**  
→ Create OAuth Client (Setup > Integrations), copy ID to Ghost Settings

**"Invalid token"**  
→ Token expired (1 hour). Call `/refresh_bearer_token` with refresh token.

**"OTP Code required"**  
→ Send OTP first: `/send_otp`, then include code in conversion request.

---

## 📊 What You Get

✅ Instant anonymous user sessions  
✅ OAuth2 bearer token authentication  
✅ OTP verification (email/SMS)  
✅ Seamless ghost → real user conversion  
✅ All data preserved on conversion  
✅ Token refresh for seamless UX  
✅ Auto-cleanup of expired ghosts  
✅ Rate limiting & security  
✅ Mobile-friendly (no cookies)  
✅ Production-ready  

---

## 🤝 Contributing

PRs welcome! 

**Quick start:**
```bash
git clone https://github.com/muneeb141/ghost
cd ghost
# Make changes, run tests
bench --site dev run-tests --app ghost
```

---

## 📜 License

MIT License - Use it however you want!

---

## 💬 Support

- 🐛 [Report Issues](https://github.com/muneeb141/ghost/issues)
- 💡 [Request Features](https://github.com/muneeb141/ghost/discussions)
- 📖 [Full Docs](docs/FULL_README.md)

---

**Made with ❤️ for the Frappe community**

*Stop losing users at the signup wall. Try Ghost today!*
