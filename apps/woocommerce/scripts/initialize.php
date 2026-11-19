<?php
// Run inside the WordPress container; the shared source remains read-only.
declare(strict_types=1);
class AdapterFailure extends RuntimeException {}
$stage = 'bootstrap';
$completed = false;
register_shutdown_function(function () use (&$completed): void {
    // Native fatal handlers can terminate PHP with exit zero; never treat that as success.
    if (!$completed) { fwrite(STDERR, "ERROR: Native initialization did not finish. Preserve configuration and inspect app logs.\n"); exit(1); }
});
try {
    $stage = 'prepare native files';
    $deadline = time() + 90;
    while (!is_file('/var/www/html/wp-config.php')) {
        if (time() >= $deadline) { throw new AdapterFailure('WordPress files are not ready. Inspect app logs.'); }
        sleep(1);
    }
    define('WP_INSTALLING', true);
    require '/var/www/html/wp-load.php';
    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    require_once ABSPATH . 'wp-admin/includes/plugin.php';
    require_once ABSPATH . 'wp-admin/includes/image.php';
    $store = json_decode(file_get_contents('/fuzcake-data/records/store.json'), true, 512, JSON_THROW_ON_ERROR);
    $catalogue = json_decode(file_get_contents('/fuzcake-data/records/catalogue.json'), true, 512, JSON_THROW_ON_ERROR);
    $url = 'http://127.0.0.1:' . getenv('HTTP_PORT');
    $stage = 'install WordPress';
    if (!is_blog_installed()) {
        global $wpdb;
        if ($wpdb->get_col('SHOW TABLES')) { throw new AdapterFailure('The database contains tables but WordPress installation is incomplete. Restore the matching database and web volume before retrying; no existing tables were cleared.'); }
        wp_install($store['name'], 'avery', getenv('ADMIN_EMAIL'), false, '', getenv('ADMIN_PASSWORD'));
        $administrator = get_user_by('login', 'avery');
        wp_update_user(['ID' => $administrator->ID, 'first_name' => $store['roles']['ADMIN']['first_name'],
            'last_name' => $store['roles']['ADMIN']['last_name'], 'display_name' => $store['roles']['ADMIN']['first_name'] . ' ' . $store['roles']['ADMIN']['last_name']]);
        // Only the brand-new installation may remove WordPress placeholder content.
        wp_delete_post(1, true);
        wp_delete_post(2, true);
        update_option('home', $url);
        update_option('siteurl', $url);
        update_option('blogdescription', $store['tagline']);
        update_option('permalink_structure', '/%postname%/');
        update_option('woocommerce_currency', $catalogue['currency']);
        update_option('woocommerce_store_address', $store['addresses'][0]['street']);
        update_option('woocommerce_store_city', $store['addresses'][0]['city']);
        update_option('woocommerce_store_postcode', $store['addresses'][0]['postal_code']);
        update_option('woocommerce_default_country', 'US');
        update_option('woocommerce_allow_tracking', 'no');
        update_option('woocommerce_enable_guest_checkout', 'yes');
        update_option('woocommerce_cod_settings', ['enabled' => 'yes', 'title' => 'Pay on delivery', 'description' => 'Pay when your fragrance order arrives.']);
        switch_theme('fuzcake');
    } elseif (untrailingslashit((string)get_option('home')) !== $url) {
        throw new AdapterFailure('HTTP_PORT differs from the installed site URL. Restore the original port; use native WordPress tools for an intentional URL migration.');
    }
    $stage = 'activate WooCommerce';
    if (!is_plugin_active('woocommerce/woocommerce.php')) {
        $activated = activate_plugin('woocommerce/woocommerce.php');
        if (is_wp_error($activated)) { throw new AdapterFailure('WooCommerce activation failed. Inspect app logs.'); }
    }
    // Activation happens in this request, so load its registered classes before seeding.
    if (!class_exists('WC_Product_Simple')) { require_once WP_PLUGIN_DIR . '/woocommerce/woocommerce.php'; }
    if (!did_action('woocommerce_init')) { WC()->init(); }
    WC_Post_Types::register_taxonomies();
    WC_Post_Types::register_post_types();
    WC_Install::create_pages();
    $categories = [];
    foreach ($catalogue['categories'] as $record) {
        $term = get_term_by('slug', 'fuzcake-' . $record['id'], 'product_cat');
        if (!$term) {
            $created = wp_insert_term($record['name'], 'product_cat', ['slug' => 'fuzcake-' . $record['id']]);
            if (is_wp_error($created)) { throw new AdapterFailure('Cannot create a product category.'); }
            $categories[$record['id']] = (int)$created['term_id'];
        } else { $categories[$record['id']] = (int)$term->term_id; }
    }
    $stage = 'seed catalogue';
    foreach ($catalogue['products'] as $record) {
        $stage = 'seed catalogue ' . $record['sku'];
        if (wc_get_product_id_by_sku($record['sku'])) { continue; }
        $product = new WC_Product_Simple();
        $product->set_name($record['name']);
        $product->set_sku($record['sku']);
        $product->set_description($record['description'] . ' ' . $record['size']);
        $product->set_short_description($record['brand']);
        $product->set_status('publish');
        $product->set_regular_price($record['price']);
        $product->set_manage_stock(true);
        $product->set_stock_quantity((int)$record['stock']);
        $product->set_category_ids([$categories[$record['category']]]);
        $source = '/fuzcake-data/assets/' . $record['image'];
        if (!is_file($source) || is_link($source)) { throw new AdapterFailure('A shared product photograph is missing or linked.'); }
        $upload = wp_upload_bits($record['sku'] . '.png', null, file_get_contents($source));
        if ($upload['error']) { throw new AdapterFailure('Cannot copy product media into WordPress uploads.'); }
        $attachment = wp_insert_attachment(['post_title' => $record['name'], 'post_mime_type' => 'image/png', 'post_status' => 'inherit'], $upload['file']);
        if (!$attachment || is_wp_error($attachment)) { throw new AdapterFailure('Cannot register product media.'); }
        wp_update_attachment_metadata($attachment, wp_generate_attachment_metadata($attachment, $upload['file']));
        $product->set_image_id($attachment);
        $product->save();
    }
    $stage = 'seed customer';
    if (!email_exists(getenv('CUSTOMER_EMAIL'))) {
        $id = wp_insert_user(['user_login' => 'mira', 'user_pass' => getenv('CUSTOMER_PASSWORD'),
            'user_email' => getenv('CUSTOMER_EMAIL'), 'role' => 'customer',
            'first_name' => $store['roles']['CUSTOMER']['first_name'], 'last_name' => $store['roles']['CUSTOMER']['last_name']]);
        if (is_wp_error($id)) { throw new AdapterFailure('Cannot create the fictional customer account.'); }
    }
    if (!get_option('fuzcake_shipping_initialized')) {
        $partners = json_decode(file_get_contents('/fuzcake-data/records/partners.json'), true, 512, JSON_THROW_ON_ERROR);
        $zone = new WC_Shipping_Zone(0);
        $carrier = array_values(array_filter($partners['carriers'], fn(array $record): bool => $record['id'] === 'fuzcake-delivery'))[0];
        $instance = $zone->add_shipping_method('flat_rate');
        if (!$instance) { throw new AdapterFailure('Cannot create local delivery method.'); }
        update_option('woocommerce_flat_rate_' . $instance . '_settings', ['title' => $carrier['name'], 'tax_status' => 'none', 'cost' => $carrier['fee']]);
        update_option('fuzcake_shipping_initialized', true);
    }
    flush_rewrite_rules();
    $completed = true;
    echo "WooCommerce store and shared catalogue are ready. Existing products and accounts were preserved.\n";
} catch (Throwable $error) {
    file_put_contents('/private/seed-diagnostic.log', $stage . ': ' . get_class($error) . ': ' . $error->getMessage() . "\n", FILE_APPEND | LOCK_EX);
    @chmod('/private', 0700);
    @chmod('/private/seed-diagnostic.log', 0644);
    fwrite(STDERR, "ERROR: Native step [" . $stage . "] failed (" . get_class($error) . ").\n");
    if ($error instanceof AdapterFailure) { fwrite(STDERR, "ERROR: " . $error->getMessage() . "\n"); }
    // Do not expose SQL connection strings or generated credentials in terminal logs.
    fwrite(STDERR, "ERROR: WordPress/WooCommerce initialization failed. Keep .env and volumes; inspect app logs and rerun setup after correcting configuration.\n");
    exit(1);
}
