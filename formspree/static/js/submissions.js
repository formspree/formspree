var settingsDropDownContent = $("#settings-dropdown-content")[0];

$(window).click(function(e) {
    if(!e.target.matches('#settings-button') && e.target.nodeName != 'path' && e.target.nodeName != 'svg') {

        if (settingsDropDownContent.classList.contains("show")) {
            settingsDropDownContent.classList.remove("show");
        }
    }
});

$(document).ready(function() {
    $("#settings-button").click(function() {
        settingsDropDownContent.classList.toggle("show");
    });
});

