// Add slashes to date field
document.addEventListener("DOMContentLoaded", function () {
  const input = document.querySelector('[data-mask="date"]');
  input.addEventListener("input", function (e) {
    let value = input.value.replace(/\D/g, "").slice(0, 8);
    let formatted = "";

    if (value.length >= 2) {
      formatted += value.slice(0, 2) + "/";
    }
    if (value.length >= 4) {
      formatted += value.slice(2, 4) + "/";
    }
    if (value.length > 4) {
      formatted += value.slice(4);
    }
    input.value = formatted;
  });
});
