document.addEventListener('click', function (event) {
    const link = event.target.closest('a');
    if (!link) return;
    if (!link.href) return;
    trackLinkClick(link);
});

function trackLinkClick(link) {
    const payload = {
        link: link.href,
        text: link.textContent.trim(),
        location: window.location.href,
        timestamp: Date.now()
    };

    const url = '/api/analytics/link_clicked';
    fetch(url, {
        method: "POST",
        body: JSON.stringify(payload),
        headers: {"Content-Type": "application/json"},
        credentials: "include",
        keepalive: true
    }).catch(() => {
    });
}
