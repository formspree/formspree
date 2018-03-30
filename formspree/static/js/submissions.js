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

$(document).ready(function() {
    $(':checkbox').change(function() {
        targetAttributeBox = this;
        var target;
        var checkedStatus = this.checked;
        var status = $("#status");

        if (this.id == 'recaptcha') {
            target = '/forms/' + hashid + '/toggle-recaptcha';
        } else if (this.id == 'email-notifications') {
            target = '/forms/' + hashid + '/toggle-emails';
        } else if (this.id == 'submission-storage') {
            target = '/forms/' + hashid + '/toggle-storage';
        }

        $.ajax({
            url: target,
            method: 'POST',
            data: {'checked': checkedStatus},
            contentType: 'application/json',
            data: JSON.stringify({
                checked: checkedStatus
            }),
            dataType: 'json',
            beforeSend: function() {
                status.removeClass("error");
                status.html('Saving... <i class="fas fa-circle-notch fa-spin"></i>');
            },
            success: function (data) {
                status.html('Saved <i class="fas fa-check-circle"></i>');
                console.log(data);
            },
            error: function (data) {
                status.html('Error saving <i class="fas fa-times-circle"></i>');
                status.addClass("error");
                targetAttributeBox.checked = !checkedStatus;
                console.log(data);
            }
        });
    })
});
