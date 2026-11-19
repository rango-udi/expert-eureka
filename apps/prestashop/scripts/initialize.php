<?php
// Install without upstream fixtures, then use native ObjectModel services for shared records.
declare(strict_types=1);
class AdapterFailure extends RuntimeException {}
$stage = 'bootstrap';
$completed = false;
register_shutdown_function(function () use (&$completed): void {
    // Native fatal handlers can terminate PHP with exit zero; never treat that as success.
    if (!$completed) { exit(1); }
});
try {
    $stage = 'prepare native files';
    $deadline = time() + 120;
    while (!is_file('/var/www/html/config/config.inc.php')) {
        if (time() >= $deadline) { throw new AdapterFailure('PrestaShop files are not ready.'); }
        sleep(1);
    }
    $store = json_decode(file_get_contents('/fuzcake-data/records/store.json'), true, 512, JSON_THROW_ON_ERROR);
    $catalogue = json_decode(file_get_contents('/fuzcake-data/records/catalogue.json'), true, 512, JSON_THROW_ON_ERROR);
    $stage = 'install database';
    if (!is_file('/var/www/html/app/config/parameters.php')) {
        $database = new PDO('mysql:host=db;port=3306;dbname=commerce', 'commerce', getenv('DB_PASSWORD'), [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
        $tables = (int)$database->query('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()')->fetchColumn();
        if ($tables !== 0) { throw new AdapterFailure('The database contains tables but native configuration is missing. Restore the matching web volume/configuration; the installer will not clear existing tables.'); }
        $arguments = [PHP_BINARY, '-d', 'memory_limit=512M', '/var/www/html/install/index_cli.php',
            '--domain=127.0.0.1:' . getenv('HTTP_PORT'), '--db_server=db:3306', '--db_name=commerce',
            '--db_user=commerce', '--db_password=' . getenv('DB_PASSWORD'), '--prefix=ps_', '--db_clear=0', '--db_create=0',
            '--firstname=' . $store['roles']['ADMIN']['first_name'], '--lastname=' . $store['roles']['ADMIN']['last_name'],
            '--password=' . getenv('ADMIN_PASSWORD'), '--email=' . getenv('ADMIN_EMAIL'), '--name=' . $store['name'],
            '--language=en', '--country=US', '--all_languages=0', '--fixtures=0', '--newsletter=0', '--send_email=0', '--ssl=0'];
        // An argument array avoids shell interpolation of private credentials.
        $installerLog = fopen('/private/prestashop-install.log', 'wb');
        if ($installerLog === false) { throw new AdapterFailure('Cannot write apps/prestashop/.runtime/prestashop-install.log. Check the runtime folder permissions.'); }
        // Both streams share one file offset so stderr cannot be overwritten by stdout.
        $process = proc_open($arguments, [0 => ['file', '/dev/null', 'r'], 1 => $installerLog, 2 => $installerLog], $pipes);
        if (!is_resource($process)) { throw new AdapterFailure('The native installer process could not be started. Check PHP proc_open availability.'); }
        $installerCode = proc_close($process);
        fclose($installerLog);
        if ($installerCode !== 0) {
            $output = (string)file_get_contents('/private/prestashop-install.log');
            foreach (['DB_PASSWORD', 'DB_ROOT_PASSWORD', 'ADMIN_PASSWORD', 'CUSTOMER_PASSWORD'] as $key) {
                $secret = getenv($key);
                if ($secret !== false && strlen($secret) >= 4) { $output = str_replace([$secret, rawurlencode($secret)], '[hidden]', $output); }
            }
            $output = preg_replace('/\x1b\[[0-?]*[ -\/]*[@-~]/', '', $output);
            foreach (array_slice(explode("\n", trim($output)), -24) as $line) {
                if (trim($line) !== '') { fwrite(STDERR, 'ERROR: Installer output: ' . substr($line, 0, 1200) . "\n"); }
            }
            throw new AdapterFailure('PrestaShop installer failed (exit ' . $installerCode . '). Run cmdc diagnostics --app prestashop; the persistent log is apps/prestashop/.runtime/prestashop-install.log.');
        }
    }
    require '/var/www/html/config/config.inc.php';
    if ((string)Configuration::get('PS_SHOP_DOMAIN') !== '127.0.0.1:' . getenv('HTTP_PORT')) {
        throw new AdapterFailure('HTTP_PORT differs from the installed domain. Restore the original port.');
    }
    $context = Context::getContext();
    $context->shop = new Shop(1);
    $context->language = new Language((int)Configuration::get('PS_LANG_DEFAULT'));
    $context->currency = new Currency((int)Configuration::get('PS_CURRENCY_DEFAULT'));
    $languages = Language::getLanguages(false);
    $translated = function (string $text) use ($languages): array {
        $values = [];
        foreach ($languages as $language) { $values[(int)$language['id_lang']] = $text; }
        return $values;
    };
    $stage = 'seed categories';
    $categories = [];
    foreach ($catalogue['categories'] as $record) {
        $slug = 'fuzcake-' . $record['id'];
        $id = (int)Db::getInstance()->getValue('SELECT id_category FROM ' . _DB_PREFIX_ . 'category_lang WHERE link_rewrite="' . pSQL($slug) . '"');
        if (!$id) {
            $category = new Category();
            $category->name = $translated($record['name']);
            $category->link_rewrite = $translated($slug);
            $category->id_parent = (int)Configuration::get('PS_HOME_CATEGORY');
            $category->active = true;
            if (!$category->add()) { throw new AdapterFailure('Cannot create category.'); }
            $id = (int)$category->id;
        }
        $categories[$record['id']] = $id;
    }
    $stage = 'seed catalogue';
    foreach ($catalogue['products'] as $record) {
        $stage = 'seed catalogue ' . $record['sku'];
        if (Product::getIdByReference($record['sku'])) { continue; }
        // Commit a new SKU only after its stock and all native thumbnails exist.
        if (!Db::getInstance()->execute('START TRANSACTION')) { throw new AdapterFailure('Cannot start product transaction.'); }
        $product = new Product();
        $product->reference = $record['sku'];
        $product->name = $translated($record['name']);
        $product->link_rewrite = $translated(Tools::str2url($record['name']));
        $product->description = $translated($record['description'] . ' ' . $record['size']);
        $product->description_short = $translated($record['brand']);
        $product->price = (float)$record['price'];
        $product->id_category_default = $categories[$record['category']];
        $product->id_tax_rules_group = 0;
        $product->active = true;
        $product->available_for_order = true;
        $product->show_price = true;
        $product->visibility = 'both';
        if (!$product->add()) { throw new AdapterFailure('Cannot create product.'); }
        $product->addToCategories([$product->id_category_default, (int)Configuration::get('PS_HOME_CATEGORY')]);
        StockAvailable::setQuantity((int)$product->id, 0, (int)$record['stock']);
        $image = new Image();
        $image->id_product = $product->id;
        $image->position = 1;
        $image->cover = true;
        if (!$image->add()) { throw new AdapterFailure('Cannot create product media.'); }
        $source = '/fuzcake-data/assets/' . $record['image'];
        if (!is_file($source) || is_link($source)) { throw new AdapterFailure('Shared product photograph missing.'); }
        $path = $image->getPathForCreation();
        if (!ImageManager::resize($source, $path . '.jpg')) { throw new AdapterFailure('Cannot create native product image.'); }
        foreach (ImageType::getImagesTypes('products') as $type) {
            if (!ImageManager::resize($source, $path . '-' . stripslashes($type['name']) . '.jpg', (int)$type['width'], (int)$type['height'])) { throw new AdapterFailure('Cannot create product thumbnail.'); }
        }
        if (!Db::getInstance()->execute('COMMIT')) { throw new AdapterFailure('Cannot commit product transaction.'); }
    }
    $stage = 'seed customer';
    if (!Customer::customerExists(getenv('CUSTOMER_EMAIL'))) {
        $customer = new Customer();
        $customer->firstname = $store['roles']['CUSTOMER']['first_name'];
        $customer->lastname = $store['roles']['CUSTOMER']['last_name'];
        $customer->email = getenv('CUSTOMER_EMAIL');
        $customer->passwd = Tools::hash(getenv('CUSTOMER_PASSWORD'));
        $customer->active = true;
        $customer->id_default_group = (int)Configuration::get('PS_CUSTOMER_GROUP');
        if (!$customer->add()) { throw new AdapterFailure('Cannot create fictional customer.'); }
    }
    // Keep the installer inaccessible after successful initialization.
    if (is_dir('/var/www/html/install')) {
        $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator('/var/www/html/install', FilesystemIterator::SKIP_DOTS), RecursiveIteratorIterator::CHILD_FIRST);
        foreach ($iterator as $path) { $path->isDir() ? rmdir($path->getPathname()) : unlink($path->getPathname()); }
        rmdir('/var/www/html/install');
    }
    $completed = true;
    echo "PrestaShop store and shared catalogue are ready. Existing products and accounts were preserved.\n";
} catch (Throwable $error) {
    file_put_contents('/private/seed-diagnostic.log', $stage . ': ' . get_class($error) . ': ' . $error->getMessage() . "\n", FILE_APPEND | LOCK_EX);
    @chmod('/private', 0700);
    @chmod('/private/seed-diagnostic.log', 0644);
    fwrite(STDERR, "ERROR: Native step [" . $stage . "] failed (" . get_class($error) . ").\n");
    if ($error instanceof AdapterFailure) { fwrite(STDERR, "ERROR: " . $error->getMessage() . "\n"); }
    if (class_exists('Db', false)) { Db::getInstance()->execute('ROLLBACK'); }
    fwrite(STDERR, "ERROR: PrestaShop initialization failed. Run cmdc diagnostics --app prestashop. Keep .env and volumes before retrying.\n");
    exit(1);
}
