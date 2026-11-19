<?php get_header(); ?>
<main>
<?php if (is_front_page()) { ?>
<section class="hero"><p>fuzcake Fragrance House</p><h1>A little scent.<br><span>A lasting feeling.</span></h1><div>Discover considered fragrances for everyday rituals and unforgettable evenings.</div></section>
<?php echo do_shortcode('[products limit="16" columns="4" orderby="id" order="ASC"]'); ?>
<?php } elseif (function_exists('is_woocommerce') && is_woocommerce()) { woocommerce_content(); }
else { while (have_posts()) { the_post(); the_content(); } } ?>
</main>
<?php get_footer(); ?>
