# Paywalls now work on the web

Source: https://www.revenuecat.com/blog/company/paywalls-on-the-web/
Imported: 2026-05-09
Published: 2025-12-31
Category: growth
Extraction method: trafilatura

## Extracted Notes

If you already use RevenueCat Paywalls on mobile, you can now use those same paywalls in the browser.
The paywalls you’ve designed for iOS and Android now render on the web, using the same layouts and components.
One paywall across mobile and web
Web paywalls aren’t a separate object or a new paywall type. They’re the web version of the paywalls you already create at the Offering level.
An Offering can include mobile products, web products, or both. When it includes both, the same paywall layout serves mobile and web users.
Your structure, copy, and experiments carry over automatically. You design a paywall once and use it across platforms.
Where web paywalls show up
You can use web paywalls in two places, depending on how your product is set up.
Inside Web Purchase Links
Web Purchase Links are RevenueCat-hosted checkout URLs. If a link uses the default package selection page, you can replace that step with your paywall.
Users see your messaging, layout, and pricing context before checkout begins. You control the experience earlier in the flow, where it matters most.
Embedded in your web app with Purchases.js
If you use Purchases.js, you can now render paywalls directly inside your web app. Call presentPaywall
, pass the HTML element where it should appear, and RevenueCat handles the rest.
The paywall renders in place and continues into checkout without custom UI or hand-built flows.
Works with Web Billing and Paddle
Web paywalls support both RevenueCat Web Billing and Paddle.
Which products appear depends on the web config attached to the surface showing the paywall. A Web Purchase Link connected to a Paddle config shows Paddle products. Switch that same link to a Web Billing config and it shows Web Billing products instead.
The paywall layout stays consistent while the product source changes based on configuration.
Change paywalls without shipping updates
Web paywalls are hosted and server driven.
You can update copy, layouts, pricing blocks, and calls to action from the dashboard. When you publish, changes go live immediately.
You can also target paywalls by country, platform, app version, or custom segments. Experiments work the same way they do on mobile, so you can test pricing, layout, or messaging on the web with the same tools.
When something stops converting, you can respond the same day.
Run subscriptions from one place
You can embed web paywalls directly into your app or link to them through hosted URLs. Either way, you manage subscription flows for mobile and web from the same system, using the same paywalls and workflows.
