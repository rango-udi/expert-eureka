/* Give the native product page a working Order Now action through local checkout. */
document.addEventListener('DOMContentLoaded', function () {
  const button = document.querySelector('.order-btn');
  if (!button) return;
  button.addEventListener('click', async function () {
    if (document.body.dataset.auth !== 'true') { window.location.href = '/users/login/'; return; }
    const product = document.querySelector('.ordr-crt-share button[data-product]');
    if (!product || product.disabled) return;
    const quantity = document.querySelector('.qty-product input[name="quantity"]');
    button.disabled = true;
    try {
      const response = await fetch('/cart/api/add/', {method: 'POST', headers: {
        'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken')},
        body: JSON.stringify({product_id: product.dataset.product, quantity: quantity ? quantity.value : 1})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'The product could not be added.');
      window.location.href = '/cart/checkout/';
    } catch (error) { window.Swal.fire({title: 'Review your selection', text: error.message}); }
    finally { button.disabled = false; }
  });
});
