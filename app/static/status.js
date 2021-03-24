document.addEventListener("DOMContentLoaded", function(){
  setTimeout(check_reload, 10000);
});

function check_reload() {
  var cb = document.getElementById("status_auto_checkbox");
  if(cb.checked) {
    window.location.reload(1);
    console.log("reloaded");
  }
  setTimeout(check_reload, 10000);
}
