/* Reuse Shuup's Bootstrap Select; retain original fields, values and change events. */
(function ($) {
  'use strict';
  function enhance(select) {
    if (!$.fn.selectpicker || !select.matches('main select.form-control')) return;
    var field = $(select);
    if (field.data('selectpicker')) {
      field.selectpicker('refresh');
    } else {
      field.addClass('selectpicker').selectpicker({
        container: 'body', liveSearch: true, size: 8, style: 'btn-default', width: '100%'
      });
    }
    var label = select.id && document.querySelector('label[for="' + CSS.escape(select.id) + '"]');
    var picker = field.data('selectpicker');
    if (label && picker && picker.$button) picker.$button.attr('aria-label', label.textContent.trim());
  }
  $(function () {
    document.querySelectorAll('main select.form-control').forEach(enhance);
  });
  // Regions replaces an input with a select or rebuilds its options on country change.
  document.addEventListener('regionFieldInitialized', function (event) {
    if (event.detail && event.detail.field) enhance(event.detail.field);
  });
}(jQuery));
