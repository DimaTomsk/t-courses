function isTest() {
    const host = window.location.hostname;
    return host === "localhost";
}

const TEST_CAPTCHA = 'test-captcha';

function pushEvent(enve_name) {
    const event = {
        event: enve_name
    };
    window.ttm = window.ttm || [];
    window.ttm.push(event);
}

function onFormSucceed(form_name) {
    if (form_name === 'common/register') {
        pushEvent("accountFormSubmit")
    } else if (form_name.startsWith("tags/")) {
        pushEvent("eventFormSubmit");
    }
}

function onFormOpen(form_name) {
    if (form_name === 'common/register') {
        pushEvent("clickButtonRegistrationAccount")
    } else if (form_name.startsWith("tags/")) {
        pushEvent("clickButtonRegistrationEvent");
    }
}

function logoutClicked() {
    fetch('/api/auth/logout', {
        method: 'POST',
    })
        .then(response => {
            return response.json();
        })
        .then(response => {
            if (response.success) {
                window.location.reload();
            } else {
            }
        })
        .catch(err => {
            console.error(err);
        });
}

function usersComponent() {
    return {
        modal_mode: null,
        form_message: null,
        username: '',
        password: '',
        form_data: {},
        active_captcha: null,

        onCaptchaLoad(el) {
            this.form_data['captcha'] = TEST_CAPTCHA;
            if (!window.smartCaptcha) {
                return;
            }
            this.active_captcha = window.smartCaptcha.render(el, {
                sitekey: 'ysc1_ffwDZn6f8uXaq0gi0zUhpYbw5DIZjUZ2TpaMW8ne14a4d94c',
                invisible: true,
                // test: true,
                hideShield: true,
                callback: (token) => {
                    if (typeof token === "string" && token.length > 0) {
                        this.form_data['captcha'] = token;
                        this.formNextStep()
                    }
                },
            });
        },

        async startForm(sequence, path, title, form_name) {
            onFormOpen(form_name)
            this.form_message = null;
            if ('captcha' in this.form_data) {
                delete this.form_data.captcha;
            }
            if (sequence.length === 0) {
                this.modal_mode = {
                    'type': null,
                    'sequence': sequence,
                    'pos': 0,
                    'path': path,
                    'title': title,
                    'form_name': form_name
                };
                await this.formNextStep();
            } else {
                this.modal_mode = {
                    'type': 'form',
                    'sequence': sequence,
                    'pos': 0,
                    'path': path,
                    'title': title,
                    'form_name': form_name
                };
            }
        },

        currentForm() {
            return this.modal_mode["sequence"][this.modal_mode["pos"]];
        },

        isNotModalMode() {
            return this.modal_mode === null || this.modal_mode['type'] === null;
        },
        async formNextStep() {
            if (this.modal_mode["pos"] + 1 < this.modal_mode["sequence"].length) {
                this.modal_mode["pos"] += 1;
                return;
            }
            this.form_message = null;

            const has_captcha = "captcha" in this.form_data;
            if (has_captcha) {
                if (isTest()) {
                } else if (this.form_data['captcha'] === TEST_CAPTCHA) {
                    window.smartCaptcha.execute(this.active_captcha)
                    return;
                }
            }

            const raw_response = await fetch(this.modal_mode['path'], {
                method: 'POST', headers: {
                    'Content-Type': 'application/json'
                }, body: JSON.stringify(this.form_data)
            });
            const data = await raw_response.json();
            if (!raw_response.ok || !data["success"]) {
                this.form_message = {"type": "error", "msg": data.detail || 'Что-то пошло не так...'};
            } else {
                onFormSucceed(this.modal_mode["form_name"])
                if (data["reload"]) {
                    window.location.reload();
                }
                if (data["detail"]) {
                    this.form_message = {"type": "info", "msg": data.detail};
                } else {
                    this.form_message = null;
                }
                if (data["reset_form"]) {
                    this.form_data = {};
                }
            }

            if (has_captcha && !isTest()) {
                window.smartCaptcha.reset(this.active_captcha);
                this.form_data['captcha'] = TEST_CAPTCHA
            }
        },

        formPrevStep() {
            this.form_message = null;
            this.modal_mode["pos"] -= 1;
        },

        closeModal() {
            this.modal_mode = null;
        },
    }
}

