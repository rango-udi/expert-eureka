<?php
// Preserve native WooCommerce cart, checkout and account templates.
add_action('after_setup_theme', function () {
    add_theme_support('title-tag');
    add_theme_support('post-thumbnails');
    add_theme_support('woocommerce');
});
add_action('wp_enqueue_scripts', function () {
    wp_enqueue_style('fuzcake', get_stylesheet_uri(), [], '1.0.0');
});
