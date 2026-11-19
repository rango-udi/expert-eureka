/* Small local notification API used by the native Wowy event handlers. */
(function () {
  let finishCurrent = null;
  window.Swal = {
    close: function () { if (finishCurrent) finishCurrent(false); },
    showLoading: function () {},
    fire: function (options, message, icon) {
      window.Swal.close();
      if (typeof options === 'string') options = {title: options, text: message, icon: icon};
      options = options || {};
      return new Promise(function (resolve) {
        const previous = document.activeElement;
        const overlay = document.createElement('div'); overlay.className = 'wowy-notification';
        const box = document.createElement('div'); box.setAttribute('role', 'alertdialog'); box.setAttribute('aria-modal', 'true');
        const title = document.createElement('h2'); title.id = 'wowy-notification-title'; title.textContent = options.title || 'Store update';
        box.setAttribute('aria-labelledby', title.id); box.appendChild(title);
        const detail = document.createElement('p'); detail.textContent = options.text || ''; box.appendChild(detail);
        let closed = false;
        function finish(confirmed) {
          if (closed) return; closed = true; overlay.remove(); finishCurrent = null;
          if (previous && previous.isConnected) previous.focus();
          resolve({isConfirmed: confirmed, isDismissed: !confirmed});
        }
        finishCurrent = finish;
        if (options.showConfirmButton !== false) {
          const button = document.createElement('button'); button.textContent = options.confirmButtonText || 'OK';
          button.addEventListener('click', function () { finish(true); }); box.appendChild(button);
        }
        if (options.showCancelButton) {
          const button = document.createElement('button'); button.textContent = options.cancelButtonText || 'Cancel';
          button.addEventListener('click', function () { finish(false); }); box.appendChild(button);
        }
        overlay.appendChild(box); document.body.appendChild(overlay);
        const first = box.querySelector('button'); box.tabIndex = -1; if (first) first.focus(); else box.focus();
        box.addEventListener('keydown', function (event) {
          if (event.key === 'Escape') finish(false);
          if (event.key === 'Tab') {
            const buttons = Array.from(box.querySelectorAll('button'));
            if (!buttons.length) { event.preventDefault(); return; }
            const edge = event.shiftKey ? buttons[0] : buttons[buttons.length - 1];
            if (document.activeElement === edge) { event.preventDefault(); buttons[event.shiftKey ? buttons.length - 1 : 0].focus(); }
          }
        });
        if (options.timer) window.setTimeout(function () { finish(false); }, options.timer);
        if (typeof options.didOpen === 'function') options.didOpen();
      });
    }
  };
}());
