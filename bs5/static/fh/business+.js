axios.interceptors.response.use(function (response) {
    // hook response
    let content = "";

    let message = response.data.message;
    // if (response.headers.token !== undefined) {
    //     let token = response.headers.token;
    //     localStorage.setItem('token', token);
    //     console.log(token);
    // }
    if (response.status === 403) {
        window.location.assign('/login');
        return
    }

    if (message === undefined) {
        return response;
    }
    if (typeof message === 'object' && Object.keys(message).length !== 0) {
        content = Object.values(message).join('<br>');
    } else if (typeof message === 'string') {
        content = message;
    }

    if (response.data.status) {
        // 执行成功
        // 仍然有消息要显示
        if (content) {
            confirm_tip('INFO! ', content)
        }
    } else {
        // 执行失败
        // confirm 强制显示
        if (content) {
            confirm_tip('WARNING! ', content)
        }
    }
    return response;
});


let DSPM = {
    'model': {},
    'app': '',
    'show': function (mid) {
        $("#" + mid).modal('show');
    },
    'hide': function (mid) {
        $("#" + mid).modal('hide');
    },
    'fresh': function (mid, data) {
        let i;
        let field;
        let fields = $("#" + mid + ' .f-data');

        console.log('fresh', data);
        for (i = 0; i < fields.length; i++) {
            field = fields[i];
            if (field.name === undefined) {
                continue
            }
            if (data[field.name] === undefined) {
                continue
            }
            console.log(field.name);
            this.fill_one(field, data[field.name]);
        }
    },
    'fill_one': function (field, value) {
        let local_name = field.localName;
        if (local_name === 'input') {
            $(field).val(value);
        } else if (local_name === 'span') {
            $(field)[0].textContent = value;
        } else if (local_name === 'select') {
            $(field).each(function () {
                let that = this;
                if ($(that).hasClass('selectpicker')) {
                    // bootstrap-select
                    $(that).selectpicker('val', value)
                } else {
                    // normal select
                    alert('normal select. ');
                }
            });
        } else if (local_name === 'textarea') {
            $(field).val(value);
        }
    },
    'json': function (mid) {
        let json = {};
        let fields = $("#" + mid + ' .f-data');
        let i, field, name;

        for (i = 0; i < fields.length; i++) {
            field = fields[i];
            name = field.name;

            let local_name = field.localName;
            let value;
            if (local_name === 'input') {
                // checkbox
                if (field.type === 'checkbox') {
                    value = field.checked;
                } else {
                    value = $(field).val();
                }
            } else if (local_name === 'span') {
                value = $(field)[0].textContent;
            } else if (local_name === 'select') {
                $(field).each(function () {
                    let that = this;
                    if ($(that).hasClass('selectpicker')) {
                        // todo: 可能会有问题
                        value = $(that).selectpicker('val');
                    } else {
                        // normal select
                        value = that.value;
                        // alert('normal select. ');
                    }
                });
            } else if (local_name === 'textarea') {
                value = $(field).val();
            }
            if (json[name] === undefined) {
                json[name] = value;
            } else {
                if (json[name] instanceof Array) {
                    json[name].push(value);
                } else {
                    let tmp = json[name];
                    json[name] = [tmp, value]
                }
            }
        }
        console.log('json', json);
        return json;
    },
    'request': function (params) {
        let that = this;
        if (params.data === undefined) {
            params.data = $("#" + this.model.id + ' form').serialize();
        }

        if (params.url === undefined) {
            params.url = this.model.url;
        }

        if (params.after !== undefined) {
            let f = params.after;
            // 已定义成功回调
            // 添加模态框收起
            function ffff(rsp, p) {
                if (that.model.id !== '') {
                    $('#' + that.model.id).modal('hide');
                    let table = $('#' + that.model.id + ' table');
                    if (table.length > 0) {
                        table.bootstrapTable('refresh');
                    }
                }
                f(rsp, p);
            }

            params.after = ffff;
        } else {
            let f = params.success;

            if (params.success === undefined) {
                // 未定义成功回调
                function ff() {
                    $('#' + that.model.id).modal('hide');
                    let table = $('#' + that.model.id + ' table');
                    if (table.length > 0) {
                        table[0].bootstrapTable('refresh');
                    }
                }

                params.success = ff;
            } else {
                // 已定义成功回调
                // 添加模态框收起
                function fff(rsp, p) {
                    if (that.model.id !== '') {
                        $('#' + that.model.id).modal('hide');
                        let table = $('#' + that.model.id + ' table');
                        if (table.length > 0) {
                            table.bootstrapTable('refresh');
                        }
                    }
                    f(rsp, p);
                }

                params.success = fff;
            }
        }

        console.log('post', params);
        if (params.m === 'post') {
            post(params);
        } else {
            get(params)
        }
    },
    'get': function (params) {
        params.m = 'get';
        this.request(params)
    },
    'post': function (params) {
        params.m = 'post';
        this.request(params)
    },
};

let ModelFH = {
    'model': {},
    'show': function (mid) {
        $("#" + mid).modal('show');
    },
    'hide': function (mid) {
        $("#" + mid).modal('hide');
    },
    'fresh': function (mid, data) {
        let i;
        let field;
        let fields = $("#" + mid + ' .f-data');

        console.log('fresh', data);
        for (i = 0; i < fields.length; i++) {
            field = fields[i];
            if (field.name === undefined) {
                continue
            }
            if (data[field.name] === undefined) {
                continue
            }
            console.log(field.name);
            this.fill_one(field, data[field.name]);
        }
    },
    'fill_one': function (field, value) {
        let local_name = field.localName;
        if (local_name === 'input') {
            $(field).val(value);
        } else if (local_name === 'span') {
            $(field)[0].textContent = value;
        } else if (local_name === 'select') {
            $(field).each(function () {
                let that = this;
                if ($(that).hasClass('selectpicker')) {
                    // bootstrap-select
                    $(that).selectpicker('val', value)
                } else {
                    // normal select
                    alert('normal select. ');
                }
            });
        } else if (local_name === 'textarea') {
            $(field).val(value);
        }
    },
    'json': function (mid) {
        let json = {};
        let fields = $("#" + mid + ' .f-data');
        let i, field, name;

        for (i = 0; i < fields.length; i++) {
            field = fields[i];
            name = field.name;

            let local_name = field.localName;
            let value;
            if (local_name === 'input') {
                // checkbox
                if (field.type === 'checkbox') {
                    value = field.checked;
                } else {
                    value = $(field).val();
                }
            } else if (local_name === 'span') {
                value = $(field)[0].textContent;
            } else if (local_name === 'select') {
                $(field).each(function () {
                    let that = this;
                    if ($(that).hasClass('selectpicker')) {
                        // todo: 可能会有问题
                        value = $(that).selectpicker('val');
                    } else {
                        // normal select
                        value = that.value;
                        // alert('normal select. ');
                    }
                });
            } else if (local_name === 'textarea') {
                value = $(field).val();
            }
            if (json[name] === undefined) {
                json[name] = value;
            } else {
                if (json[name] instanceof Array) {
                    json[name].push(value);
                } else {
                    let tmp = json[name];
                    json[name] = [tmp, value]
                }
            }
        }
        console.log('json', json);
        return json;
    },
};

function confirm_tip(title, content) {
    // 提示信息
    let confirm = $.confirm({
        closeIcon: false,
        columnClass: 'col-md-12',
        theme: 'supervan',
        type: 'red',
        title: title,
        content: content,
        buttons: {
            cancel: {
                text: 'CLOSE',
                btnClass: 'btn-warning'
            }
        }
    });
    confirm.open();
}

function request(params) {
    let url = params.url;
    let method = params.method;
    let data = params.data;
    let success = params.success;
    let success_params = params.success_params;
    let failed = params.failed;
    let failed_params = params.failed_params;
    let btn = params.btn;
    let header = params.header;
    let after = params.after;
    let after_params = params.after_params;

    if (header === undefined) {
        header = {}
    }

    let config;
    if (method === "get") {
        let tk = $.url().param('tk');
        let u;
        if (tk !== undefined) {
            data['tk'] = tk
        }
        config = {url: url, method: method, params: data, headers: header}
    } else if (method === 'post') {
        config = {url: url, method: method, data: data, headers: header}
    }

    if (btn !== undefined) {
        btn.attr('disabled', 'true');
    }
    axios.request(config)
        .then(function (response) {
            // 结束回调
            if (after !== undefined) {
                after(response, after_params)
            } else {
                // 正常回调
                if (response.data.status) {
                    if (success !== undefined) {
                        success(response, success_params);
                    }
                }
                // 错误回调
                else {
                    if (failed !== undefined) {
                        failed(response, failed_params);
                    }
                }
            }
            if (btn !== undefined) {
                btn.attr('disabled', false);
            }
        })
        .catch(function (error) {
            if (btn !== undefined) {
                btn.attr('disabled', false);
            }
            // console.log(error);
        });
}

function post(params) {
    params.method = 'post';
    request(params)
}

function get(params) {
    params.method = 'get';
    request(params)
}

function adjust_height(table) {
    // let height = $(document).height() - table.offset().top;
    // console.log('document', $(document).height());
    // console.log(table.offset().top);
    // table.bootstrapTable('resetView', {height: height});
    // table.bootstrapTable('refresh');
}

function search_move(table) {
    let $search = $("#top-search");
    let $input = $(".search input");
    $search.empty();
    $search.append($(".fixed-table-toolbar"));

    $(".search").css("width", '100%');

    $input.addClass('form-control-dark w-100');
    $input.css("width", '100%');
    $input.attr('placeholder', '搜索');

    if (table === undefined)
        return;
    adjust_height(table);
}

function get_selected($table, with_version) {
    let data = $table.bootstrapTable('getSelections');
    let ids_ = [];
    let versions_ = [];
    if (data.length === 0) {
        return {}
    }
    for (let i = 0; i < data.length; i++) {
        ids_.push(data[i].id);
        if (with_version) {
            versions_.push(data[i].version);
        }
    }
    if (with_version) {
        return {'ids': ids_.join(','), 'versions': versions_.join(',')};
    }
    return {'ids': ids_.join(',')};
}

function confirm_do_with_table(model, Model, title) {
    model.$btn.confirm({
        closeIcon: true,
        theme: 'supervan',
        title: title,
        content: "",
        onOpenBefore: function () {
            let select = get_selected(Model.$table, false);
            if (!select.ids) {
                this.setContent("<h3>PLEASE SELECT ITEM(S)</h3>");
                this.buttons.doKey.hide();
            } else {
                this.setContent("ARE YOU SURE TO " + title + " THESE ITEM(S)?");
            }
        },
        buttons: {
            doKey: {
                text: 'YES',
                action: function () {
                    let select = get_selected(Model.$table, false);
                    get({
                        'url': model.u, 'btn': model.$btn, 'data': {'target': select.ids},
                        'success': function () {
                            Model.$table.bootstrapTable('refresh');
                        }
                    });
                }
            },
            cancel: {text: 'CLOSE'}
        }
    });
}

function confirm_do_ns(model, Model, title) {
    model.$btn.confirm({
        closeIcon: true,
        theme: 'supervan',
        title: title,
        content: "",
        onOpenBefore: function () {
            this.setContent("ARE YOU SURE TO " + title + "?");
        },
        buttons: {
            doKey: {
                text: 'YES',
                action: function () {
                    let params;
                    params = {
                        'kid': '',
                        'action': model.action,
                        'is_parallel': false,
                        'params': {'target': ''}
                    };
                    if (model.$btn.id !== undefined) {
                        params.kid = model.$btn.id
                    }
                    console.info(params);
                    Model.io.emit(Model.signal, params);
                }
            },
            cancel: {text: 'CLOSE'}
        }
    });
}

// function commit_viewer(model, Model, with_target) {
//     model.$btn.on('click', function () {
//         let params = Model.json(model.modal_id);
//
//         if (with_target) {
//             if (Model.target) {
//                 params.target = Model.target + '/' + params.target;
//             }
//         }
//         if (model.suffix) {
//             params.target = params.target + model.suffix;
//         }
//         console.info('params', params);
//         get({
//             'url': model.u,
//             'data': params,
//             'btn': model.$btn,
//             'success': function (rsp) {
//                 get({
//                     'url': model.u,
//                     'btn': model.$btn,
//                     'success': function (rsp) {
//                         let $vw = $("#viewer_md");
//                         $vw.empty();
//                         $vw.append('<div id="viewer"><textarea style="display:none;" class="form-control f-data" name="text" spellcheck="false" tabindex="0" wrap="off"></textarea></div>');
//                         $vw.append('<img id="im" class="img-fluid" src="">');
//                         let type = rsp.data.type;
//                         let rows = rsp.data.rows;
//                         if (type === 'txt') {
//                             editormd('viewer', {
//                                 width: "100%",
//                                 height: "825px",
//                                 watch: false,
//                                 theme: "dark",
//                                 mode: "python",
//                                 toolbar: false,
//                                 value: rows,
//                                 searchReplace: true,
//                                 codeFold: true,
//                                 syncScrolling: "single",
//                                 path: "/static/editor.md/lib/"
//                             });
//                         }
//                     }
//                 });
//             }
//         });
//     });
// }

function commit_from_model(model, Model, with_target) {
    model.$btn.on('click', function () {
        let params = Model.json(model.modal_id);

        if (with_target) {
            if (Model.target) {
                params.target = Model.target + '/' + params.target;
            }
        }
        if (model.suffix) {
            params.target = params.target + model.suffix;
        }
        console.info('params', params);
        get({
            'url': model.u,
            'data': params,
            'btn': model.$btn,
            'success': function (rsp) {
                window.location.reload();
            }
        });
    });
}

function emit_from_model(model, Model) {
    model.$btn.on('click', function () {
        let params = {
            'kid': '',
            'action': model.action,
            'is_parallel': false,
            'params': Model.json(model.modal_id)
        };
        if (this.id !== undefined) {
            params.kid = this.id
        }
        console.log('params', params);
        Model.io.emit(Model.signal, params);
    });
}

function list_for_table(model, Model, fn) {

    Model.$table.bootstrapTable('refreshOptions', {
        queryParams: function (params) {
            if (Model.target !== undefined) {
                params.target = Model.target;
            }
            params.search = $('#top-search').val();
            return params
        },
        ajax: function (request) {
            get({
                'url': model.u,
                'data': request.data,
                'success': function (rsp) {
                    request.success({
                        row: rsp.data
                    });
                    let parents = rsp.data.parents;
                    console.log(parents);

                    let $parents = $("#parents");
                    $parents.empty();
                    $parents.append("<strong>#: </strong>");

                    let u = '/webs/' + rsp.data.app + '/index';
                    let ps = [];
                    for (let i = 0; i < parents.length; i++) {
                        ps.push("<a href='" + u + "?target=" + parents[i]['i_path'] + '&tk=' + tk + "'><strong>" + parents[i]['i'] + "</strong></a>");
                    }
                    $parents.append(ps.join(' / '));
                    if (fn !== undefined) {
                        $parents.append('<strong><span>' + fn + '</span></strong>');
                    }
                    Model.$table.bootstrapTable('load', rsp.data);
                }
            })
        },
    });

    search_move(Model.$table);
    $(window).resize(function () {
        adjust_height(Model.$table);
    });

    // $("#refresh").on('click', function () {
    //     Model.$table.bootstrapTable('refresh');
    // });

    $("#search").on('click', function () {
        Model.$table.bootstrapTable('refresh');
    });
}

function show_modal_if_select_table(model, Model) {
    model.$btn.on('click', function () {
        let select = get_selected(Model.$table, false);
        if (!select.ids) {
            confirm_tip("WARNING", "<h3>PLEASE SELECT ITEM(S)</h3>");
        } else {
            let modal = new bootstrap.Modal(document.getElementById(model.modal_id), {
                keyboard: false
            });
            $('#' + model.modal_id + ' input[name=target]').val(select.ids);
            modal.show();
        }
    })
}

function escape(srcString) {
    let result = srcString;
    // 正则表达式中的特殊字符
    let chars_js = ["\\", "^", "$", "*", "?", ".", "+", "(", ")", "[", "]", "|", "{", "}"];
    // 不是正则表达式中的特殊字符
    let chars_special = ["~", "`", "@", "#", "%", "&", "=", "'", "\"", ":", ";", "<", ">", ",", "/"];
    for (let i = 0; i < chars_js.length; i++) {
        result = result.replace(new RegExp("\\"
            + chars_js[i], "g"), "\\"
            + chars_js[i]);
    }
    for (let i = 0; i < chars_special.length; i++) {
        result = result.replace(new RegExp(chars_special[i],
            "g"), "\\" + chars_special[i]);
    }
    return result;
}

function operateFormatter(value, row) {
    if (row.isdir) {
        return ''
    }
    let ctx = '<div class="btn-group" role="group">';
    // star
    if (row.star) {
        ctx += '<button type="button" name="' + row.app + ',' + row.afp + '" class="btn btn-outline-danger btn-sm star_remove">';
        ctx += '<i class="fa-solid fa-fw fa-heart"></i></button>';
    } else {
        ctx += '<button type="button" name="' + row.app + ',' + row.afp + '" class="btn btn-outline-info btn-sm star_favorite">';
        ctx += '<i class="fa-solid fa-fw fa-heart"></i></button>';
    }
    // dsp his
    if (row.app === 'dsp:yft' || row.app === 'dsp:yfd') {
        // ctx += '<button type="button" name="' + row.afp + '" class="btn btn-outline-dark btn-sm his-btn">';
        // ctx += '<i class="fas fa-fw fa-fw fa-history"></i></button>';
    }
    // know:site
    if (row.app === 'know:site') {
        ctx += '<button type="button" name="' + row.afp + '" class="btn btn-outline-secondary btn-sm visit-btn">';
        ctx += '<i class="fa-solid fa-fw fa-link"></i></button>';
    }
    // his
    if (row.app === 'history') {
        // ctx += '<button type="button" name="' + row.app + ',' + row.afp + '" data-bs-toggle="modal" data-bs-target="#view-only-modal" class="btn btn-outline-success btn-sm view-btn">'
        // ctx += '<i class="fa-solid fa-eye"></i></button>'
    }
    //timing
    if (row.app === 'timing' && row.STATUS) {
        ctx += '<button disable type="button" class="btn btn-outline-warning btn-sm">';
        ctx += '<i class="fa-solid fa-fw fa-toggle-off"></i></button>';
    }
    if (row.app === 'timing' && !row.STATUS) {
        ctx += '<button disable type="button" class="btn btn-outline-info btn-sm">';
        ctx += '<i class="fa-solid fa-fw fa-toggle-on"></i></button>';
    }
    ctx += '</div>';
    return ctx
}

function operatesSpatio(value, row) {
    return '<div class="btn-group" role="group">' +
        '<button type="button" name="" class="btn btn-outline-info btn-sm">' +
        '<i class="fa-solid fa-fw fa-file"></i></button>' +
        '<button type="button" name="" class="btn btn-outline-info btn-sm">' +
        '<i class="fa-solid fa-fw fa-eye"></i></button>' +
        '<button type="button" name="" class="btn btn-outline-info btn-sm">' +
        '<i class="fa-solid fa-fw fa-download"></i></button>' +
        '<button type="button" name="" class="btn btn-outline-info btn-sm">' +
        '<i class="fa-solid fa-fw fa-rotate-backward"></i></button>' +
        '</div>';
}

function iFormatter(value, row, index) {
    let options = $table.bootstrapTable('getOptions');
    return options.pageSize * (options.pageNumber - 1) + index + 1;
}

function iSpatio(value, row, index) {
    let options = $("#spatio").bootstrapTable('getOptions');
    return options.pageSize * (options.pageNumber - 1) + index + 1;
}

function fileViewFormatter(value, row) {
    if (!row.isdir) {
        return '<button class="link-primary btn btn-sm view-file" name="' + row.app + ',' + row.afp + '">' + value + '</button>'
    }
    return '<a class="btn-sm" href="/webs/' + row.app + '/index?target=' + row.afp + '&tk=' + tk + '"><strong>' + value + '</strong></a>'
}

function detailFormatter(index, row) {
    let ctx = '';
    ctx += 'app: ' + row.app + '<br>';
    ctx += 'afp: ' + row.afp + '<br>';
    ctx += 'size: ' + row.size + '<br>';
    ctx += 'ctime: ' + row.ctime + '<br>';
    ctx += 'mtime: ' + row.mtime + '<br>';
    return '<pre>' + ctx + '</pre>';
}

