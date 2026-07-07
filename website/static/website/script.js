document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.schedule-check').forEach(function (cb) {
        cb.addEventListener('change', function () {
            this.closest('form').submit();
        });
    });
});
