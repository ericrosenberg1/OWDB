tinymce.init({
    selector: '.tinymce-editor',
    menubar: false,
    plugins: 'lists link',
    toolbar: 'undo redo | bold italic underline | bullist numlist | link',
    branding: false,
    statusbar: false,
    height: 300,
    content_style: "body { font-family:Arial,sans-serif; font-size:14px }",
    skin: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'oxide-dark' : 'oxide',
    content_css: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'default',
    paste_as_text: true
});
