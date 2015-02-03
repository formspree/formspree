/*!
 * jQuery Tiny Modal
 * @author: Cedric Ruiz
 * https://github.com/elclanrs/jquery.tiny.modal
 */
(function($) {

  var _defaults = {
    buttons: ['Ok','Cancel'],
    title: 'Alert',
    html: '<p>Alert</p>',
    Ok: $.noop,
    Cancel: $.noop,
    onOpen: $.noop,
    onClose: $.noop,
    clickOutside: true
  };

  $.tinyModal = function(opts) {

    var o = $.extend({}, _defaults, opts),
        $overlay = $('<div class="tinymodal-overlay">').hide(),
        $modal = $('<div class="tinymodal-window">\
          <div class="tinymodal-title">'+ o.title +'<div class="tinymodal-close">&#215;</div></div>\
          <div class="tinymodal-content"></div>\
          <div class="tinymodal-buttons"><div class="inner"></div></div>\
          </div>').hide(),
        $el = $(o.html)
        $children = $el.children();

    $modal.find('.tinymodal-content').append($children);
    
    if (o.buttons.length) {
      $modal.find('.inner').append('<button>'+ o.buttons.join('</button><button>') +'</button>');
    }

    function show() {
      $('body').width($('body').width()).css('overflow', 'hidden');
      $overlay.fadeIn('fast', function() {
        $modal.fadeIn('fast', o.onOpen);
      });
      $modal.css({
        marginLeft: -($modal.width()/2) +'px',
      });
    }

    function hide(callback) {
      $modal.fadeOut('fast', function() {
        $('body').css({ width: 'auto', overflow: 'auto' });
        $overlay.fadeOut('fast');
        if (typeof callback == 'function') callback();
        $el.append($children);
      });
    }

    $modal.find('.tinymodal-buttons button, .tinymodal-close').on('click', function(e) {
      var callback = $(this).text();
      hide(o[callback]);
    });

    $modal.find('.tinymodal-close').click(o.onClose);

    $modal.on('click', function(e){ e.stopPropagation(); });

    if (o.clickOutside) $overlay.on('click', hide);

    $('body').prepend($overlay.append($modal));
    show();
  };

}(jQuery));
