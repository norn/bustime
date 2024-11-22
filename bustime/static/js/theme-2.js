BUS_SIDE_IMG = "static/img/pumpkin";
CAT_IMG = "/static/img/zombie.png";

function session_timer() {
    if (isiPad || is_ios || isWP || isOperaMini) {
        return;
    }
    var w;
    var h;
    var r;
    $('.busnumber').each(function(index) {
        if (Math.random() > 0.92) {
            w = 80 * (1.5 - Math.random());
            h = 34 * (1.5 - Math.random());
            r = -20 + 40 * Math.random();

            w = parseInt(w, 10);
            h = parseInt(h, 10);
            r = parseInt(r, 10);
            $(this).css('transform', 'rotate(' + r + 'deg)');
        }
    });

    setTimeout(function() {
        session_timer();
    }, Math.random() * 1000);
}
session_timer();