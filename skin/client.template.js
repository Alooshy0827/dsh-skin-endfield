// Self-contained, dependency-free client. All visual changes belong to one effect.
window.__ModuleLoader__.load({
  id: "dsh-skin-local",
  factory: () => {
    const tokens = /* TOKEN_OVERRIDES */ {};
    const css = /* SKIN_CSS */ "";
    const STYLE_ID = "dsh-endfield-skin-style";
    const ATTR = "data-dsh-endfield-skin";
    return {
      inject: ["theme"],
      apply(ctx) {
        if (!ctx?.theme?.overrideTokens || !ctx?.effect) return;
        ctx.effect(() => {
          if (!document.head || !document.body || document.getElementById(STYLE_ID)) return;
          const body = document.body;
          const previous = body.getAttribute(ATTR);
          const style = document.createElement("style");
          let revokeTokens;
          let intro;
          let timer;
          let disposed = false;
          const removeIntro = () => {
            if (timer !== undefined) window.clearTimeout(timer);
            timer = undefined;
            intro?.remove();
            intro = undefined;
          };
          const dispose = () => {
            if (disposed) return;
            disposed = true;
            removeIntro();
            style.remove();
            if (previous === null) body.removeAttribute(ATTR);
            else body.setAttribute(ATTR, previous);
            if (typeof revokeTokens === "function") revokeTokens();
          };
          try {
            // Two arguments are required by the installed DSH Theme facade.
            revokeTokens = ctx.theme.overrideTokens("dsh-skin-local", tokens);
            style.id = STYLE_ID;
            style.textContent = css;
            document.head.appendChild(style);
            body.setAttribute(ATTR, "0.2.1");

            // No layout participation, focus change, or input capture.
            if (typeof window.matchMedia === "function" &&
                !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
              intro = document.createElement("div");
              intro.className = "dsh-ef-intro";
              intro.setAttribute("aria-hidden", "true");
              intro.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:2147483000";
              const wordmark = document.createElement("div");
              wordmark.className = "dsh-ef-wordmark";
              for (const [index, text] of ["DEEPSEEK", "HARNESS"].entries()) {
                const line = document.createElement("span");
                line.className = `dsh-ef-wordmark-line dsh-ef-wordmark-line-${index}`;
                line.textContent = text;
                wordmark.appendChild(line);
              }
              intro.appendChild(wordmark);
              // Set a fail-safe before attachment, independent of animation events.
              timer = window.setTimeout(removeIntro, 1000);
              body.appendChild(intro);
            }
          } catch (error) {
            dispose();
            console.warn("[dsh-skin-local] Skin could not load; original appearance restored.", error);
          }
          return dispose;
        }, "dsh-skin-local: appearance and startup");
      },
    };
  },
});
