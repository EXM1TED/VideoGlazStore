document.addEventListener("DOMContentLoaded", () => {
    const links = document.querySelectorAll(".main-nav a");
    const path = window.location.pathname.replace(/\/+$/, "") || "/";

    links.forEach((link) => {
        const href = (link.getAttribute("href") || "").replace(/\/+$/, "") || "/";
        if (href === path) {
            link.classList.add("active");
            link.setAttribute("aria-current", "page");
        }
    });
});
