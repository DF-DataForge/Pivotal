$(document).ready(function() {
  function get_wk_offset() {
    var offset = new Date().getTimezoneOffset(),
      abs_offset = Math.abs(offset),
      hours = abs_offset / 60;
    return offset < 0 ? +hours : -hours;
  }

  function sync_backend_frontend(state, url) {
    if (state == "confirmed" && $("#auction_start_at").html() != undefined) {
      console.log(state, $("#auction_start_at").html(), "AUCTION SET TO RUN");
      location.reload(true);
    }
    if (
      state == "running" ||
      (state == "extend" && $("#auction_end_on").html() != undefined)
    ) {
      console.log(state, $("#auction_end_on").html(), "AUCTION SET TO END");
      location.reload(true);
    }

    var el = $(".auction_stop").closest("#wk_auction_status")
    el.find(".auction_stop").remove();
    el.find(".row").remove();
    el.find(".col-md-12").remove();
  }

  $(this)
    .find(".countdown")
    .each(function() {
      if ($(this).data("wk_time_left") != undefined) {
        var wk_time_date = $(this).data("wk_time_left");
        wk_time_date = wk_time_date.replace(/\s/, "T");
        var now = new Date(wk_time_date);
        var d = new Date(
          now.getUTCFullYear(),
          now.getUTCMonth(),
          now.getUTCDate(),
          now.getUTCHours(),
          now.getUTCMinutes(),
          now.getUTCSeconds()
        );
        var formated_date =
          d.getMonth() +
          1 +
          "/" +
          d.getDate() +
          "/" +
          d.getFullYear() +
          " " +
          d.getHours() +
          ":" +
          d.getMinutes() +
          ":" +
          d.getSeconds();
        $(this).downCount(
          {
            date: formated_date,
            offset: -get_wk_offset()
          },
          sync_backend_frontend.bind(
            null,
            $(this).data("wk_auction_state"),
            location.href
          )
        );
      }
    });

    $('#more').click(function(){
      console.log($(this).prev())
      if ($(this).prev().css('display')=="none"){
          $(this).text('more');
          $(this).prev().css('display','');
          $(this).prev().prev().addClass('d-none')
      }
      else{
        $(this).text('...less');
        $(this).prev().css('display','none');
        $(this).prev().prev().removeClass('d-none')
      }
    })
});
