/** @odoo-module **/

import { deserializeDateTime } from "@web/core/l10n/dates";

$(document).ready(function() {


  if (location.href.indexOf("biderr") != -1) {
    $(".bid_error")
      .show()
      .fadeOut(8000);
      location.hash = location.hash.replace('biderr' , '');
    
  } else if (location.href.indexOf("bid_notallow") != -1) {
    $(".bid_notallow")
      .show()
      .fadeOut(8000);
  } else if (location.href.indexOf("bidsubmit") != -1) {
    $(".bid_submited")
      .show()
      .fadeOut(8000);
      location.hash = location.hash.replace('bidsubmit' , '');
  } else if (location.href.indexOf("loginfirst") != -1) {
    $(".loginfirst")
      .show(500)
      .fadeOut(8000);
  } else if (location.href.indexOf("minbid") != -1) {
    $(".minbid_error")
      .show(500)
      .fadeOut(8000);
      location.hash = location.hash.replace('minbid' , '');
  } else if (location.href.indexOf("autobid") != -1) {
    $(".autobid_error")
      .show(500)
      .fadeOut(8000);
  } else if (location.href.indexOf("unsubscribed") != -1) {
    console.log("unsubscribed");
    $(".bid_unsubscribe")
      .show(500)
      .fadeOut(8000);
    location.hash = location.hash.replace('unsubscribed' , '');
  } else if (location.href.indexOf("subscribe") != -1) {
    $(".bid_subscribe")
    .show(500)
    .fadeOut(8000);
    location.hash = location.hash.replace('subscribe' , '');
  }

  if (window.location.pathname.includes("/shop/product")) {
    // moment.js is no longer shipped with Odoo: format with luxon
    // (deserializeDateTime returns a luxon DateTime in the user timezone).
    var span1 = $(this).find("#auction_week_left_public");
    if (span1) {
      var date = $("#auction_week_left_public").data("date");
      try {
        var new_date = deserializeDateTime(date).toFormat("cccc dd-MMM-yyyy, h:mma");
        $("#auction_week_left_public").text(new_date);
      } catch (e) {
        console.log(e);
      }
    }
    var span2 = $(this).find("#auction_start_week_left_public");
    if (span2) {
      var date = $("#auction_start_week_left_public").data("start-date");
      try {
        var new_date = deserializeDateTime(date).toFormat("cccc dd-MMM-yyyy, h:mma");
        $("#auction_start_week_left_public").text(new_date);
      } catch (e) {
        console.log(e);
      }
    }
  }

  $('#auction_subscription').click(function(){
    $(this).closest('div').attr('disabled','disabled');
  })

});
