document.addEventListener("DOMContentLoaded", function () {
    var modalId = "{{ modal_id }}";
    var modalElem = document.getElementById(modalId);

    if (!modalElem) return;

    (function(id) {
      window["showModal_" + id] = function(contentId) {
        var el = document.getElementById(id);
        if (!el) return;

        if (contentId) {
          var source = document.getElementById(contentId);
          var target = el.querySelector(".modal-body-placeholder");
          if (source && target) {
            target.innerHTML = source.innerHTML;
          } else {
            console.warn("[Modal] Content not found for ID:", contentId);
          }
        }

        el.style.display = "flex";
      };

      window["hideModal_" + id] = function() {
        var el = document.getElementById(id);
        if (el) {
          el.style.display = "none";
        }
      };

      modalElem.addEventListener("click", function(event) {
        if (event.target === modalElem) {
          window["hideModal_" + id]();
        }
      });
    })(modalId);
  });