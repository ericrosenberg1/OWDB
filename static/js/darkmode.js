function toggleDarkMode() {
    const html = document.querySelector('html');
    const currentTheme = html.getAttribute('data-bs-theme');
    html.setAttribute('data-bs-theme', currentTheme === 'light' ? 'dark' : 'light');
}
