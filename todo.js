"use strict";
var userid = null;
var monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug',
    'Sep', 'Oct', 'Nov', 'Dec'];

function twoDigit(n) {
    return "0123456789"[Math.floor(n / 10) % 10] +  "0123456789"[n % 10];
}

function ajax_send(request, success) {
    $.ajax('/todo', {
        data: { json: JSON.stringify(request) },
        dataType: 'json',
        success: success,
        error: function (e) { ui_error('Internal error'); }
    });
}
function ajax_login(email) {
    ajax_send({ action: 'getUserFromEmail', email: email },
        function (e) {
            if (e.error)
                $('#loginError').show().text(e.error);
            else
                ui_login(e);
        });
}
function ajax_register(email, name) {
    ajax_send({ action: 'addUser', email:email, name:name },
        function (e) {
            if (e.error)
                $('#loginError').show().text(e.error);
            else {
                e.name = name;
                e.email = email;
                ui_login(e);
            }
        });
}
function ajax_getItems(done) {
    ajax_send({ action: 'getUserItems', user: userid, done: done },
        function (e) {
            if (e.error)
                ui_error(e.error);
            else
                ui_populateItems(e);
        });
}
function ajax_addItem(due, title) {
    ajax_send({ action: 'addItem', user: userid, due: due, title: title },
        function (e) {
            if (e.error)
                ui_error(e.error);
            else
                ui_getItems();
        });
}
function ajax_completeItem(id, done) {
    ajax_send({ action: 'completeItem', id:id, done:done },
        function (e) {
            if (e.error)
                ui_error(e.error);
            else
                ui_getItems();
        });
}

function ui_setDaysOfMonth(year, month) {
    var monthLength = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    var html = [];
    if (new Date(year, 1, 29).getMonth() == 1)
        monthLength[2] = 28;
    for (var i = 1; i <= monthLength[month]; i++)
        html.push('<option value=' + i + '>' + i)
    $('#date').html(html.join('\n'));
}
function ui_setToday() {
    var date = new Date();
    $('#year').val(date.getFullYear());
    ui_setDaysOfMonth(date.getFullYear(), date.getMonth() + 1);
    $('#month').val(date.getMonth());
    $('#date').val(date.getDate());
}

function ui_error(message) {
    $('#shade').show();
    $('#errorBox').show();
    $('#errorText').text(message);
}
function ui_getItems() {
    ajax_getItems($('#onlyIncomplete').is(':checked')? false: null);
}
function ui_addItem() {
    var due = new Date(
        $('#year').val(),
        $('#month').val(),
        $('#date').val(),
        $('#hour').val(),
        $('#minute').val());
    ajax_addItem(due, $('#title').val());
}
function ui_login(user) {
    userid = user.id;
    $('#nameIndicator').text(user.name);
    $('#login').hide();
    $('#main').show();
    ui_getItems(null);
}
function ui_toggleComplete(e) {
    var id = +$(e.target).parent().attr('id').replace('item-', '');
    ajax_completeItem(id, $(e.target).is(':checked'));
}

// Setup UI events & values
function ui_setup() {
    var output;
    var i, hour;
    for (output = [], i = 0; i < 24; i++)
        output.push('<option value=' + i + '>' + twoDigit(i % 12 || 12) + (i < 11? 'am': 'pm'));
    $('#hour').html(output.join('\n'));
    for (output = [], i = 0; i < 60; i++)
        output.push('<option value=' + i + '>' + twoDigit(i));
    $('#minute').html(output.join('\n'));

    $('#errorOK').click(function() {
        $('#shade').show();
        $('#errorBox').hide();
    });
    
    // Handle ajax_login through click and enter button
    function event_login(e) {
        ajax_login($('#email').val());
        e.preventDefault();
    }
    function event_register(e) {
        ajax_register($('#email').val(), $('#name').val());
        e.preventDefault();
    }
    $('#login').submit(event_login);
    $('#loginButton').click(event_login);
    $('#registerButton').click(event_register);
    
    // Set the number of days per month when the year or month changes
    $('#month, #year').change(function () {
        var oldDate = $('#date').val();
        ui_setDaysOfMonth($('#year').val(), $('#month').val());
        $('#date').val(oldDate);
    });
    
    $('#today').click(ui_setToday)
    
    // Add task
    function event_addItem(e) {
        ui_addItem();
        e.preventDefault();
    }
    $('#addItem').click(event_addItem);
    $('#toolbar').submit(event_addItem);
    
    $('#onlyIncomplete, #oldestFirst').change(function () { ui_getItems(); });
}
function ui_populateItems(items) {
    function itemToHtml(item) {
        var due = new Date(item.due);
        var dueDate = twoDigit(due.getDate()) + ' ' +
            monthNames[due.getMonth() + 1] + 
            (due.getFullYear() != new Date().getFullYear()? ' ' + due.getFullYear(): '');
        var dueTime = twoDigit(due.getHours() % 12 || 12) + ':' + twoDigit(due.getMinutes()) +
            (due.getHours() < 12? 'am': 'pm');
        var overdue = new Date() > due;
        
        return '<div class="item' + (overdue? ' overdue': '') + '" id=item-' + item.id + '>' +
            '<input type=checkbox ' + (item.done? 'checked': '') + ' onchange="ui_toggleComplete(event)" >' +
            '<span class=due>' +
                '<span class=dueDate>' + dueDate + '</span> ' +
                '@ <span class=dueTime>' + dueTime + '</span>' +
            '</span>' +
            '<span class=title>' + item.title + '</span>' +
            '</div>';
    }
    function itemsToHtml(items) {
        var output = items.map(itemToHtml);
        return output.join('\n');
    }
    function latestFirst(a, b) {
        return a.due < b.due? 1: a.due > b.due? -1: 0;
    }
    function oldestFirst(a, b) {
        return a.due < b.due? -1: a.due > b.due? 1: 0;
    }
    
    items.forEach(function(i) { i.due = new Date(i.due); });
    items = items.sort($('#oldestFirst').is(':checked')? oldestFirst: latestFirst);
    
    var html = itemsToHtml(items);
    $('#well').html(html);
}

jQuery(document).ready(function($) {
    ui_setup();
    ui_setToday();
});