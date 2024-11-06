function js_page_extra() {
    console.log("План-наряд");
    //$("#route0").on("click", ".delete_button", busstop_delete);
    $('select').on('change', pchange);
    $('.ui.dropdown').dropdown();
    // $('.ui.dropdown').dropdown({
    // onChange: pchange
    // });
}
function pchange() {
    //value, text, sitem
    //JSON.stringify(route)
    // if (typeof sitem === 'string') {
    //     console.log(sitem);
    //     return;
    // }
    //sitem
    var plan_id = $(this).parent().parent().attr('name');
    console.log(plan_id);

    var obj = $(this);
    obj.addClass('color-0-bg');
    setTimeout(function() {
        obj.removeClass('color-0-bg');
    }, 400);

    var gnum =$("[name=gnum_"+plan_id).val();
    var gra = $("[name=gra_"+plan_id).val();
    var request = $.ajax({
        url: "/ajax/plan_change/",
        type: "post",
        data: {
            city_id: city_id,
            plan_id: plan_id,
            gra: gra,
            gnum: gnum,
        }
    });
}