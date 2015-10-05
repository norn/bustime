document_ready = function() {
    var FastClick = require('fastclick');
    FastClick.attach(document.body);

    $(".launch").click(function() {
        $('.ui.sidebar').sidebar('toggle');
    });

    VK.init({
        apiId: 3767256,
        onlyWidgets: true
    });

    VK.Widgets.Like("vk_like", {
        type: "button",
        pageUrl: "http://www.bustime.ru"
    });

    // VK.Widgets.Like("vk_like_tablet", {
    //     type: "button",
    //     pageUrl: "http://www.bustime.ru"
    // });
}


