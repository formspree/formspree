function toggleCaptcha(hashid) {
    // alert('Entered js file');
    var recaptchaButton = $("#recaptcha-toggle");

    $.ajax({
        url: '/forms/'+ hashid+ '/toggle-recaptcha',
        method: 'GET',
        beforeSend: function () {
            recaptchaButton.addClass("disabled");
        },
        success: function (data) {
            recaptchaButton.removeClass("disabled");
            if (data.disabled) {
                toastr.success("Successfully turned off reCAPTCHA");
                recaptchaButton.text("Turn on reCAPTCHA");
                recaptchaButton.removeClass("destructive");
                $("#recaptcha-tooltip").attr("data-hint", "Turning on reCAPTCHA will help protect your form against spam");
            } else {
                toastr.success("Successfully turned on reCAPTCHA");
                recaptchaButton.text("Turn off reCAPTCHA");
                recaptchaButton.addClass("destructive");
                $("#recaptcha-tooltip").attr("data-hint", "Turning off reCAPTCHA will remove the intermediate screen, but make your form suceptible to spam");

            }
        },
        error: function (data) {
            console.log(data);
            toastr.error('Unable to toggle CAPTCHA at this point. Please try again later');
        }
    })
}