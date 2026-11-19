<!doctype html><html <?php language_attributes(); ?>><head><meta charset="<?php bloginfo('charset'); ?>"><meta name="viewport" content="width=device-width, initial-scale=1"><?php wp_head(); ?></head>
<body <?php body_class(); ?>><?php wp_body_open(); ?>
<header><a class="brand" href="<?php echo esc_url(home_url('/')); ?>">fuzcake<span aria-hidden="true">.</span></a><nav aria-label="Main navigation">
<a href="<?php echo esc_url(home_url('/')); ?>">Discover</a><a href="<?php echo esc_url(wc_get_page_permalink('shop')); ?>">Fragrances</a><a href="<?php echo esc_url(wc_get_page_permalink('myaccount')); ?>">My account</a><a href="<?php echo esc_url(wc_get_cart_url()); ?>">Bag</a>
</nav></header>
