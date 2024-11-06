document_ready = function() {
    if (window.screen.width > us_city_transport_count * 100) {
        for(var i=0;i<10; i++) {
            // возвращает размер шрифта в норму если экран широкий
            let t = $(".modec_"+i);
            if(t){
                t.removeClass("xsfont");
            }
        }
    }

    if (typeof(js_page_extra) === 'function') {
      js_page_extra();
    }

    var cp = Cookies.get('cookie_policy');
    if (cp === undefined) {
        $(".cookie_policy").removeClass("hidden");
    }
};   // document_ready = function()


function cookie_policy_agree() {
    Cookies.set('cookie_policy', "1", { expires: 3650 });
    $(".cookie_policy").addClass("hidden");
}
