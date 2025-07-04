/**
 * marked - a markdown parser
 * Copyright (c) 2011-2019, Christopher Jeffrey. (MIT Licensed)
 * https://github.com/markedjs/marked
 */
! function(e, t) {
    "object" == typeof exports && "undefined" != typeof module ? module.exports = t() : "function" == typeof define && define.amd ? define(t) : (e = e || self).marked = t()
}(this, function() {
    "use strict";

    function r(e, t) {
        for (var n = 0; n < t.length; n++) {
            var r = t[n];
            r.enumerable = r.enumerable || !1, r.configurable = !0, "value" in r && (r.writable = !0), Object.defineProperty(e, r.key, r)
        }
    }

    function t(e, t, n) {
        return t && r(e.prototype, t), n && r(e, n), e
    }

    function n(e) {
        return h[e]
    }
    var e, s = (function(t) {
            function e() {
                return {
                    baseUrl: null,
                    breaks: !1,
                    gfm: !0,
                    headerIds: !0,
                    headerPrefix: "",
                    highlight: null,
                    langPrefix: "language-",
                    mangle: !0,
                    pedantic: !1,
                    renderer: null,
                    sanitize: !1,
                    sanitizer: null,
                    silent: !1,
                    smartLists: !1,
                    smartypants: !1,
                    xhtml: !1
                }
            }
            t.exports = {
                defaults: e(),
                getDefaults: e,
                changeDefaults: function(e) {
                    t.exports.defaults = e
                }
            }
        }(e = {
            exports: {}
        }, e.exports), e.exports),
        i = (s.defaults, s.getDefaults, s.changeDefaults, /[&<>"']/),
        l = /[&<>"']/g,
        a = /[<>"']|&(?!#?\w+;)/,
        o = /[<>"']|&(?!#?\w+;)/g,
        h = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };
    var u = /&(#(?:\d+)|(?:#x[0-9A-Fa-f]+)|(?:\w+));?/gi;

    function c(e) {
        return e.replace(u, function(e, t) {
            return "colon" === (t = t.toLowerCase()) ? ":" : "#" === t.charAt(0) ? "x" === t.charAt(1) ? String.fromCharCode(parseInt(t.substring(2), 16)) : String.fromCharCode(+t.substring(1)) : ""
        })
    }
    var p = /(^|[^\[])\^/g;
    var g = /[^\w:]/g,
        f = /^$|^[a-z][a-z0-9+.-]*:|^[?#]/i;
    var d = {},
        k = /^[^:]+:\/*[^/]*$/,
        b = /^([^:]+:)[\s\S]*$/,
        m = /^([^:]+:\/*[^/]*)[\s\S]*$/;

    function x(e, t) {
        d[" " + e] || (k.test(e) ? d[" " + e] = e + "/" : d[" " + e] = _(e, "/", !0));
        var n = -1 === (e = d[" " + e]).indexOf(":");
        return "//" === t.substring(0, 2) ? n ? t : e.replace(b, "$1") + t : "/" === t.charAt(0) ? n ? t : e.replace(m, "$1") + t : e + t
    }

    function _(e, t, n) {
        var r = e.length;
        if (0 === r) return "";
        for (var s = 0; s < r;) {
            var i = e.charAt(r - s - 1);
            if (i !== t || n) {
                if (i === t || !n) break;
                s++
            } else s++
        }
        return e.substr(0, r - s)
    }
    var y = function(e, t) {
            if (t) {
                if (i.test(e)) return e.replace(l, n)
            } else if (a.test(e)) return e.replace(o, n);
            return e
        },
        w = c,
        v = function(e, t, n) {
            if (e) {
                var r;
                try {
                    r = decodeURIComponent(c(n)).replace(g, "").toLowerCase()
                } catch (e) {
                    return null
                }
                if (0 === r.indexOf("javascript:") || 0 === r.indexOf("vbscript:") || 0 === r.indexOf("data:")) return null
            }
            t && !f.test(n) && (n = x(t, n));
            try {
                n = encodeURI(n).replace(/%25/g, "%")
            } catch (e) {
                return null
            }
            return n
        },
        $ = function(e) {
            for (var t, n, r = 1; r < arguments.length; r++)
                for (n in t = arguments[r]) Object.prototype.hasOwnProperty.call(t, n) && (e[n] = t[n]);
            return e
        },
        S = function(e, t) {
            var n = e.replace(/\|/g, function(e, t, n) {
                    for (var r = !1, s = t; 0 <= --s && "\\" === n[s];) r = !r;
                    return r ? "|" : " |"
                }).split(/ \|/),
                r = 0;
            if (n.length > t) n.splice(t);
            else
                for (; n.length < t;) n.push("");
            for (; r < n.length; r++) n[r] = n[r].trim().replace(/\\\|/g, "|");
            return n
        },
        z = _,
        A = function(e, t) {
            if (-1 === e.indexOf(t[1])) return -1;
            for (var n = e.length, r = 0, s = 0; s < n; s++)
                if ("\\" === e[s]) s++;
                else if (e[s] === t[0]) r++;
            else if (e[s] === t[1] && --r < 0) return s;
            return -1
        },
        R = function(e) {
            e && e.sanitize && !e.silent && console.warn("marked(): sanitize and sanitizer parameters are deprecated since version 0.7.0, should not be used and will be removed in the future. Read more here: https://marked.js.org/#/USING_ADVANCED.md#options")
        },
        Z = {
            exec: function() {}
        },
        L = function(n, e) {
            n = n.source || n, e = e || "";
            var r = {
                replace: function(e, t) {
                    return t = (t = t.source || t).replace(p, "$1"), n = n.replace(e, t), r
                },
                getRegex: function() {
                    return new RegExp(n, e)
                }
            };
            return r
        },
        q = $,
        C = {
            newline: /^\n+/,
            code: /^( {4}[^\n]+\n*)+/,
            fences: /^ {0,3}(`{3,}|~{3,})([^`~\n]*)\n(?:|([\s\S]*?)\n)(?: {0,3}\1[~`]* *(?:\n+|$)|$)/,
            hr: /^ {0,3}((?:- *){3,}|(?:_ *){3,}|(?:\* *){3,})(?:\n+|$)/,
            heading: /^ {0,3}(#{1,6}) +([^\n]*?)(?: +#+)? *(?:\n+|$)/,
            blockquote: /^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/,
            list: /^( {0,3})(bull) [\s\S]+?(?:hr|def|\n{2,}(?! )(?!\1bull )\n*|\s*$)/,
            html: "^ {0,3}(?:<(script|pre|style)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n+|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?\\?>\\n*|<![A-Z][\\s\\S]*?>\\n*|<!\\[CDATA\\[[\\s\\S]*?\\]\\]>\\n*|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:\\n{2,}|$)|<(?!script|pre|style)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:\\n{2,}|$)|</(?!script|pre|style)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:\\n{2,}|$))",
            def: /^ {0,3}\[(label)\]: *\n? *<?([^\s>]+)>?(?:(?: +\n? *| *\n *)(title))? *(?:\n+|$)/,
            nptable: Z,
            table: Z,
            lheading: /^([^\n]+)\n {0,3}(=+|-+) *(?:\n+|$)/,
            _paragraph: /^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html)[^\n]+)*)/,
            text: /^[^\n]+/,
            _label: /(?!\s*\])(?:\\[\[\]]|[^\[\]])+/,
            _title: /(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/
        };
    C.def = L(C.def).replace("label", C._label).replace("title", C._title).getRegex(), C.bullet = /(?:[*+-]|\d{1,9}\.)/, C.item = /^( *)(bull) ?[^\n]*(?:\n(?!\1bull ?)[^\n]*)*/, C.item = L(C.item, "gm").replace(/bull/g, C.bullet).getRegex(), C.list = L(C.list).replace(/bull/g, C.bullet).replace("hr", "\\n+(?=\\1?(?:(?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$))").replace("def", "\\n+(?=" + C.def.source + ")").getRegex(), C._tag = "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|section|source|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul", C._comment = /<!--(?!-?>)[\s\S]*?-->/, C.html = L(C.html, "i").replace("comment", C._comment).replace("tag", C._tag).replace("attribute", / +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(), C.paragraph = L(C._paragraph).replace("hr", C.hr).replace("heading", " {0,3}#{1,6} +").replace("|lheading", "").replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}|~{3,})[^`\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)]) ").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|!--)").replace("tag", C._tag).getRegex(), C.blockquote = L(C.blockquote).replace("paragraph", C.paragraph).getRegex(), C.normal = q({}, C), C.gfm = q({}, C.normal, {
        nptable: /^ *([^|\n ].*\|.*)\n *([-:]+ *\|[-| :]*)(?:\n((?:.*[^>\n ].*(?:\n|$))*)\n*|$)/,
        table: /^ *\|(.+)\n *\|?( *[-:]+[-| :]*)(?:\n((?: *[^>\n ].*(?:\n|$))*)\n*|$)/
    }), C.pedantic = q({}, C.normal, {
        html: L("^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:\"[^\"]*\"|'[^']*'|\\s[^'\"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))").replace("comment", C._comment).replace(/tag/g, "(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(),
        def: /^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/,
        heading: /^ *(#{1,6}) *([^\n]+?) *(?:#+ *)?(?:\n+|$)/,
        fences: Z,
        paragraph: L(C.normal._paragraph).replace("hr", C.hr).replace("heading", " *#{1,6} *[^\n]").replace("lheading", C.lheading).replace("blockquote", " {0,3}>").replace("|fences", "").replace("|list", "").replace("|html", "").getRegex()
    });
    var O = {
        escape: /^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/,
        autolink: /^<(scheme:[^\s\x00-\x1f<>]*|email)>/,
        url: Z,
        tag: "^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>",
        link: /^!?\[(label)\]\(\s*(href)(?:\s+(title))?\s*\)/,
        reflink: /^!?\[(label)\]\[(?!\s*\])((?:\\[\[\]]?|[^\[\]\\])+)\]/,
        nolink: /^!?\[(?!\s*\])((?:\[[^\[\]]*\]|\\[\[\]]|[^\[\]])*)\](?:\[\])?/,
        strong: /^__([^\s_])__(?!_)|^\*\*([^\s*])\*\*(?!\*)|^__([^\s][\s\S]*?[^\s])__(?!_)|^\*\*([^\s][\s\S]*?[^\s])\*\*(?!\*)/,
        em: /^_([^\s_])_(?!_)|^\*([^\s*<\[])\*(?!\*)|^_([^\s<][\s\S]*?[^\s_])_(?!_|[^\spunctuation])|^_([^\s_<][\s\S]*?[^\s])_(?!_|[^\spunctuation])|^\*([^\s<"][\s\S]*?[^\s\*])\*(?!\*|[^\spunctuation])|^\*([^\s*"<\[][\s\S]*?[^\s])\*(?!\*)/,
        code: /^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/,
        br: /^( {2,}|\\)\n(?!\s*$)/,
        del: Z,
        text: /^(`+|[^`])(?:[\s\S]*?(?:(?=[\\<!\[`*]|\b_|$)|[^ ](?= {2,}\n))|(?= {2,}\n))/,
        _punctuation: "!\"#$%&'()*+,\\-./:;<=>?@\\[^_{|}~"
    };
    O.em = L(O.em).replace(/punctuation/g, O._punctuation).getRegex(), O._escapes = /\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/g, O._scheme = /[a-zA-Z][a-zA-Z0-9+.-]{1,31}/, O._email = /[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/, O.autolink = L(O.autolink).replace("scheme", O._scheme).replace("email", O._email).getRegex(), O._attribute = /\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/, O.tag = L(O.tag).replace("comment", C._comment).replace("attribute", O._attribute).getRegex(), O._label = /(?:\[[^\[\]]*\]|\\.|`[^`]*`|[^\[\]\\`])*?/, O._href = /<(?:\\[<>]?|[^\s<>\\])*>|[^\s\x00-\x1f]*/, O._title = /"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/, O.link = L(O.link).replace("label", O._label).replace("href", O._href).replace("title", O._title).getRegex(), O.reflink = L(O.reflink).replace("label", O._label).getRegex(), O.normal = q({}, O), O.pedantic = q({}, O.normal, {
        strong: /^__(?=\S)([\s\S]*?\S)__(?!_)|^\*\*(?=\S)([\s\S]*?\S)\*\*(?!\*)/,
        em: /^_(?=\S)([\s\S]*?\S)_(?!_)|^\*(?=\S)([\s\S]*?\S)\*(?!\*)/,
        link: L(/^!?\[(label)\]\((.*?)\)/).replace("label", O._label).getRegex(),
        reflink: L(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label", O._label).getRegex()
    }), O.gfm = q({}, O.normal, {
        escape: L(O.escape).replace("])", "~|])").getRegex(),
        _extended_email: /[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/,
        url: /^((?:ftp|https?):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/,
        _backpedal: /(?:[^?!.,:;*_~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_~)]+(?!$))+/,
        del: /^~+(?=\S)([\s\S]*?\S)~+/,
        text: /^(`+|[^`])(?:[\s\S]*?(?:(?=[\\<!\[`*~]|\b_|https?:\/\/|ftp:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@))|(?= {2,}\n|[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@))/
    }), O.gfm.url = L(O.gfm.url, "i").replace("email", O.gfm._extended_email).getRegex(), O.breaks = q({}, O.gfm, {
        br: L(O.br).replace("{2,}", "*").getRegex(),
        text: L(O.gfm.text).replace("\\b_", "\\b_| {2,}\\n").replace(/\{2,\}/g, "*").getRegex()
    });
    var D = {
            block: C,
            inline: O
        },
        E = s.defaults,
        j = D.block,
        P = z,
        T = S,
        I = y,
        B = function() {
            function n(e) {
                this.tokens = [], this.tokens.links = Object.create(null), this.options = e || E, this.rules = j.normal, this.options.pedantic ? this.rules = j.pedantic : this.options.gfm && (this.rules = j.gfm)
            }
            n.lex = function(e, t) {
                return new n(t).lex(e)
            };
            var e = n.prototype;
            return e.lex = function(e) {
                return e = e.replace(/\r\n|\r/g, "\n").replace(/\t/g, "    "), this.token(e, !0)
            }, e.token = function(e, t) {
                var n, r, s, i, l, a, o, h, u, c, p, g, f, d, k, b;
                for (e = e.replace(/^ +$/gm, ""); e;)
                    if ((s = this.rules.newline.exec(e)) && (e = e.substring(s[0].length), 1 < s[0].length && this.tokens.push({
                            type: "space"
                        })), s = this.rules.code.exec(e)) {
                        var m = this.tokens[this.tokens.length - 1];
                        e = e.substring(s[0].length), m && "paragraph" === m.type ? m.text += "\n" + s[0].trimRight() : (s = s[0].replace(/^ {4}/gm, ""), this.tokens.push({
                            type: "code",
                            codeBlockStyle: "indented",
                            text: this.options.pedantic ? s : P(s, "\n")
                        }))
                    } else if (s = this.rules.fences.exec(e)) e = e.substring(s[0].length), this.tokens.push({
                    type: "code",
                    lang: s[2] ? s[2].trim() : s[2],
                    text: s[3] || ""
                });
                else if (s = this.rules.heading.exec(e)) e = e.substring(s[0].length), this.tokens.push({
                    type: "heading",
                    depth: s[1].length,
                    text: s[2]
                });
                else if ((s = this.rules.nptable.exec(e)) && (a = {
                        type: "table",
                        header: T(s[1].replace(/^ *| *\| *$/g, "")),
                        align: s[2].replace(/^ *|\| *$/g, "").split(/ *\| */),
                        cells: s[3] ? s[3].replace(/\n$/, "").split("\n") : []
                    }).header.length === a.align.length) {
                    for (e = e.substring(s[0].length), p = 0; p < a.align.length; p++) /^ *-+: *$/.test(a.align[p]) ? a.align[p] = "right" : /^ *:-+: *$/.test(a.align[p]) ? a.align[p] = "center" : /^ *:-+ *$/.test(a.align[p]) ? a.align[p] = "left" : a.align[p] = null;
                    for (p = 0; p < a.cells.length; p++) a.cells[p] = T(a.cells[p], a.header.length);
                    this.tokens.push(a)
                } else if (s = this.rules.hr.exec(e)) e = e.substring(s[0].length), this.tokens.push({
                    type: "hr"
                });
                else if (s = this.rules.blockquote.exec(e)) e = e.substring(s[0].length), this.tokens.push({
                    type: "blockquote_start"
                }), s = s[0].replace(/^ *> ?/gm, ""), this.token(s, t), this.tokens.push({
                    type: "blockquote_end"
                });
                else if (s = this.rules.list.exec(e)) {
                    for (e = e.substring(s[0].length), o = {
                            type: "list_start",
                            ordered: d = 1 < (i = s[2]).length,
                            start: d ? +i : "",
                            loose: !1
                        }, this.tokens.push(o), n = !(h = []), f = (s = s[0].match(this.rules.item)).length, p = 0; p < f; p++) c = (a = s[p]).length, ~(a = a.replace(/^ *([*+-]|\d+\.) */, "")).indexOf("\n ") && (c -= a.length, a = this.options.pedantic ? a.replace(/^ {1,4}/gm, "") : a.replace(new RegExp("^ {1," + c + "}", "gm"), "")), p !== f - 1 && (l = j.bullet.exec(s[p + 1])[0], (1 < i.length ? 1 === l.length : 1 < l.length || this.options.smartLists && l !== i) && (e = s.slice(p + 1).join("\n") + e, p = f - 1)), r = n || /\n\n(?!\s*$)/.test(a), p !== f - 1 && (n = "\n" === a.charAt(a.length - 1), r = r || n), r && (o.loose = !0), b = void 0, (k = /^\[[ xX]\] /.test(a)) && (b = " " !== a[1], a = a.replace(/^\[[ xX]\] +/, "")), u = {
                        type: "list_item_start",
                        task: k,
                        checked: b,
                        loose: r
                    }, h.push(u), this.tokens.push(u), this.token(a, !1), this.tokens.push({
                        type: "list_item_end"
                    });
                    if (o.loose)
                        for (f = h.length, p = 0; p < f; p++) h[p].loose = !0;
                    this.tokens.push({
                        type: "list_end"
                    })
                } else if (s = this.rules.html.exec(e)) e = e.substring(s[0].length), this.tokens.push({
                    type: this.options.sanitize ? "paragraph" : "html",
                    pre: !this.options.sanitizer && ("pre" === s[1] || "script" === s[1] || "style" === s[1]),
                    text: this.options.sanitize ? this.options.sanitizer ? this.options.sanitizer(s[0]) : I(s[0]) : s[0]
                });
                else if (t && (s = this.rules.def.exec(e))) e = e.substring(s[0].length), s[3] && (s[3] = s[3].substring(1, s[3].length - 1)), g = s[1].toLowerCase().replace(/\s+/g, " "), this.tokens.links[g] || (this.tokens.links[g] = {
                    href: s[2],
                    title: s[3]
                });
                else if ((s = this.rules.table.exec(e)) && (a = {
                        type: "table",
                        header: T(s[1].replace(/^ *| *\| *$/g, "")),
                        align: s[2].replace(/^ *|\| *$/g, "").split(/ *\| */),
                        cells: s[3] ? s[3].replace(/\n$/, "").split("\n") : []
                    }).header.length === a.align.length) {
                    for (e = e.substring(s[0].length), p = 0; p < a.align.length; p++) /^ *-+: *$/.test(a.align[p]) ? a.align[p] = "right" : /^ *:-+: *$/.test(a.align[p]) ? a.align[p] = "center" : /^ *:-+ *$/.test(a.align[p]) ? a.align[p] = "left" : a.align[p] = null;
                    for (p = 0; p < a.cells.length; p++) a.cells[p] = T(a.cells[p].replace(/^ *\| *| *\| *$/g, ""), a.header.length);
                    this.tokens.push(a)
                } else if (s = this.rules.lheading.exec(e)) e = e.substring(s[0].length), this.tokens.push({
                    type: "heading",
                    depth: "=" === s[2].charAt(0) ? 1 : 2,
                    text: s[1]
                });
                else if (t && (s = this.rules.paragraph.exec(e))) e = e.substring(s[0].length), this.tokens.push({
                    type: "paragraph",
                    text: "\n" === s[1].charAt(s[1].length - 1) ? s[1].slice(0, -1) : s[1]
                });
                else if (s = this.rules.text.exec(e)) e = e.substring(s[0].length), this.tokens.push({
                    type: "text",
                    text: s[0]
                });
                else if (e) throw new Error("Infinite loop on byte: " + e.charCodeAt(0));
                return this.tokens
            }, t(n, null, [{
                key: "rules",
                get: function() {
                    return j
                }
            }]), n
        }(),
        U = s.defaults,
        F = v,
        N = y,
        X = function() {
            function e(e) {
                this.options = e || U
            }
            var t = e.prototype;
            return t.code = function(e, t, n) {
                var r = (t || "").match(/\S*/)[0];
                if (this.options.highlight) {
                    var s = this.options.highlight(e, r);
                    null != s && s !== e && (n = !0, e = s)
                }
                return r ? '<pre><code class="' + this.options.langPrefix + N(r, !0) + '">' + (n ? e : N(e, !0)) + "</code></pre>\n" : "<pre><code>" + (n ? e : N(e, !0)) + "</code></pre>"
            }, t.blockquote = function(e) {
                return "<blockquote>\n" + e + "</blockquote>\n"
            }, t.html = function(e) {
                return e
            }, t.heading = function(e, t, n, r) {
                return this.options.headerIds ? "<h" + t + ' id="' + this.options.headerPrefix + r.slug(n) + '">' + e + "</h" + t + ">\n" : "<h" + t + ">" + e + "</h" + t + ">\n"
            }, t.hr = function() {
                return this.options.xhtml ? "<hr/>\n" : "<hr>\n"
            }, t.list = function(e, t, n) {
                var r = t ? "ol" : "ul";
                return "<" + r + (t && 1 !== n ? ' start="' + n + '"' : "") + ">\n" + e + "</" + r + ">\n"
            }, t.listitem = function(e) {
                return "<li>" + e + "</li>\n"
            }, t.checkbox = function(e) {
                return "<input " + (e ? 'checked="" ' : "") + 'disabled="" type="checkbox"' + (this.options.xhtml ? " /" : "") + "> "
            }, t.paragraph = function(e) {
                return "<p>" + e + "</p>\n"
            }, t.table = function(e, t) {
                return "<table>\n<thead>\n" + e + "</thead>\n" + (t = t && "<tbody>" + t + "</tbody>") + "</table>\n"
            }, t.tablerow = function(e) {
                return "<tr>\n" + e + "</tr>\n"
            }, t.tablecell = function(e, t) {
                var n = t.header ? "th" : "td";
                return (t.align ? "<" + n + ' align="' + t.align + '">' : "<" + n + ">") + e + "</" + n + ">\n"
            }, t.strong = function(e) {
                return "<strong>" + e + "</strong>"
            }, t.em = function(e) {
                return "<em>" + e + "</em>"
            }, t.codespan = function(e) {
                return "<code>" + e + "</code>"
            }, t.br = function() {
                return this.options.xhtml ? "<br/>" : "<br>"
            }, t.del = function(e) {
                return "<del>" + e + "</del>"
            }, t.link = function(e, t, n) {
                if (null === (e = F(this.options.sanitize, this.options.baseUrl, e))) return n;
                var r = '<a href="' + N(e) + '"';
                return t && (r += ' title="' + t + '"'), r += ">" + n + "</a>"
            }, t.image = function(e, t, n) {
                if (null === (e = F(this.options.sanitize, this.options.baseUrl, e))) return n;
                var r = '<img src="' + e + '" alt="' + n + '"';
                return t && (r += ' title="' + t + '"'), r += this.options.xhtml ? "/>" : ">"
            }, t.text = function(e) {
                return e
            }, e
        }(),
        G = function() {
            function e() {
                this.seen = {}
            }
            return e.prototype.slug = function(e) {
                var t = e.toLowerCase().trim().replace(/[\u2000-\u206F\u2E00-\u2E7F\\'!"#$%&()*+,./:;<=>?@[\]^`{|}~]/g, "").replace(/\s/g, "-");
                if (this.seen.hasOwnProperty(t))
                    for (var n = t; this.seen[n]++, t = n + "-" + this.seen[n], this.seen.hasOwnProperty(t););
                return this.seen[t] = 0, t
            }, e
        }(),
        M = s.defaults,
        V = D.inline,
        H = A,
        J = y,
        K = function() {
            function u(e, t) {
                if (this.options = t || M, this.links = e, this.rules = V.normal, this.options.renderer = this.options.renderer || new X, this.renderer = this.options.renderer, this.renderer.options = this.options, !this.links) throw new Error("Tokens array requires a `links` property.");
                this.options.pedantic ? this.rules = V.pedantic : this.options.gfm && (this.options.breaks ? this.rules = V.breaks : this.rules = V.gfm)
            }
            u.output = function(e, t, n) {
                return new u(t, n).output(e)
            };
            var e = u.prototype;
            return e.output = function(e) {
                for (var t, n, r, s, i, l, a = ""; e;)
                    if (i = this.rules.escape.exec(e)) e = e.substring(i[0].length), a += J(i[1]);
                    else if (i = this.rules.tag.exec(e)) !this.inLink && /^<a /i.test(i[0]) ? this.inLink = !0 : this.inLink && /^<\/a>/i.test(i[0]) && (this.inLink = !1), !this.inRawBlock && /^<(pre|code|kbd|script)(\s|>)/i.test(i[0]) ? this.inRawBlock = !0 : this.inRawBlock && /^<\/(pre|code|kbd|script)(\s|>)/i.test(i[0]) && (this.inRawBlock = !1), e = e.substring(i[0].length), a += this.options.sanitize ? this.options.sanitizer ? this.options.sanitizer(i[0]) : J(i[0]) : i[0];
                else if (i = this.rules.link.exec(e)) {
                    var o = H(i[2], "()");
                    if (-1 < o) {
                        var h = (0 === i[0].indexOf("!") ? 5 : 4) + i[1].length + o;
                        i[2] = i[2].substring(0, o), i[0] = i[0].substring(0, h).trim(), i[3] = ""
                    }
                    e = e.substring(i[0].length), this.inLink = !0, r = i[2], s = this.options.pedantic ? (t = /^([^'"]*[^\s])\s+(['"])(.*)\2/.exec(r)) ? (r = t[1], t[3]) : "" : i[3] ? i[3].slice(1, -1) : "", r = r.trim().replace(/^<([\s\S]*)>$/, "$1"), a += this.outputLink(i, {
                        href: u.escapes(r),
                        title: u.escapes(s)
                    }), this.inLink = !1
                } else if ((i = this.rules.reflink.exec(e)) || (i = this.rules.nolink.exec(e))) {
                    if (e = e.substring(i[0].length), t = (i[2] || i[1]).replace(/\s+/g, " "), !(t = this.links[t.toLowerCase()]) || !t.href) {
                        a += i[0].charAt(0), e = i[0].substring(1) + e;
                        continue
                    }
                    this.inLink = !0, a += this.outputLink(i, t), this.inLink = !1
                } else if (i = this.rules.strong.exec(e)) e = e.substring(i[0].length), a += this.renderer.strong(this.output(i[4] || i[3] || i[2] || i[1]));
                else if (i = this.rules.em.exec(e)) e = e.substring(i[0].length), a += this.renderer.em(this.output(i[6] || i[5] || i[4] || i[3] || i[2] || i[1]));
                else if (i = this.rules.code.exec(e)) e = e.substring(i[0].length), a += this.renderer.codespan(J(i[2].trim(), !0));
                else if (i = this.rules.br.exec(e)) e = e.substring(i[0].length), a += this.renderer.br();
                else if (i = this.rules.del.exec(e)) e = e.substring(i[0].length), a += this.renderer.del(this.output(i[1]));
                else if (i = this.rules.autolink.exec(e)) e = e.substring(i[0].length), r = "@" === i[2] ? "mailto:" + (n = J(this.mangle(i[1]))) : n = J(i[1]), a += this.renderer.link(r, null, n);
                else if (this.inLink || !(i = this.rules.url.exec(e))) {
                    if (i = this.rules.text.exec(e)) e = e.substring(i[0].length), this.inRawBlock ? a += this.renderer.text(this.options.sanitize ? this.options.sanitizer ? this.options.sanitizer(i[0]) : J(i[0]) : i[0]) : a += this.renderer.text(J(this.smartypants(i[0])));
                    else if (e) throw new Error("Infinite loop on byte: " + e.charCodeAt(0))
                } else {
                    if ("@" === i[2]) r = "mailto:" + (n = J(i[0]));
                    else {
                        for (; l = i[0], i[0] = this.rules._backpedal.exec(i[0])[0], l !== i[0];);
                        n = J(i[0]), r = "www." === i[1] ? "http://" + n : n
                    }
                    e = e.substring(i[0].length), a += this.renderer.link(r, null, n)
                }
                return a
            }, u.escapes = function(e) {
                return e ? e.replace(u.rules._escapes, "$1") : e
            }, e.outputLink = function(e, t) {
                var n = t.href,
                    r = t.title ? J(t.title) : null;
                return "!" !== e[0].charAt(0) ? this.renderer.link(n, r, this.output(e[1])) : this.renderer.image(n, r, J(e[1]))
            }, e.smartypants = function(e) {
                return this.options.smartypants ? e.replace(/---/g, "—").replace(/--/g, "–").replace(/(^|[-\u2014/(\[{"\s])'/g, "$1‘").replace(/'/g, "’").replace(/(^|[-\u2014/(\[{\u2018\s])"/g, "$1“").replace(/"/g, "”").replace(/\.{3}/g, "…") : e
            }, e.mangle = function(e) {
                if (!this.options.mangle) return e;
                for (var t, n = e.length, r = "", s = 0; s < n; s++) t = e.charCodeAt(s), .5 < Math.random() && (t = "x" + t.toString(16)), r += "&#" + t + ";";
                return r
            }, t(u, null, [{
                key: "rules",
                get: function() {
                    return V
                }
            }]), u
        }(),
        Q = function() {
            function e() {}
            var t = e.prototype;
            return t.strong = function(e) {
                return e
            }, t.em = function(e) {
                return e
            }, t.codespan = function(e) {
                return e
            }, t.del = function(e) {
                return e
            }, t.text = function(e) {
                return e
            }, t.link = function(e, t, n) {
                return "" + n
            }, t.image = function(e, t, n) {
                return "" + n
            }, t.br = function() {
                return ""
            }, e
        }(),
        W = s.defaults,
        Y = $,
        ee = w,
        te = function() {
            function n(e) {
                this.tokens = [], this.token = null, this.options = e || W, this.options.renderer = this.options.renderer || new X, this.renderer = this.options.renderer, this.renderer.options = this.options, this.slugger = new G
            }
            n.parse = function(e, t) {
                return new n(t).parse(e)
            };
            var e = n.prototype;
            return e.parse = function(e) {
                this.inline = new K(e.links, this.options), this.inlineText = new K(e.links, Y({}, this.options, {
                    renderer: new Q
                })), this.tokens = e.reverse();
                for (var t = ""; this.next();) t += this.tok();
                return t
            }, e.next = function() {
                return this.token = this.tokens.pop(), this.token
            }, e.peek = function() {
                return this.tokens[this.tokens.length - 1] || 0
            }, e.parseText = function() {
                for (var e = this.token.text;
                    "text" === this.peek().type;) e += "\n" + this.next().text;
                return this.inline.output(e)
            }, e.tok = function() {
                var e = "";
                switch (this.token.type) {
                    case "space":
                        return "";
                    case "hr":
                        return this.renderer.hr();
                    case "heading":
                        return this.renderer.heading(this.inline.output(this.token.text), this.token.depth, ee(this.inlineText.output(this.token.text)), this.slugger);
                    case "code":
                        return this.renderer.code(this.token.text, this.token.lang, this.token.escaped);
                    case "table":
                        var t, n, r, s, i = "";
                        for (r = "", t = 0; t < this.token.header.length; t++) r += this.renderer.tablecell(this.inline.output(this.token.header[t]), {
                            header: !0,
                            align: this.token.align[t]
                        });
                        for (i += this.renderer.tablerow(r), t = 0; t < this.token.cells.length; t++) {
                            for (n = this.token.cells[t], r = "", s = 0; s < n.length; s++) r += this.renderer.tablecell(this.inline.output(n[s]), {
                                header: !1,
                                align: this.token.align[s]
                            });
                            e += this.renderer.tablerow(r)
                        }
                        return this.renderer.table(i, e);
                    case "blockquote_start":
                        for (e = "";
                            "blockquote_end" !== this.next().type;) e += this.tok();
                        return this.renderer.blockquote(e);
                    case "list_start":
                        e = "";
                        for (var l = this.token.ordered, a = this.token.start;
                            "list_end" !== this.next().type;) e += this.tok();
                        return this.renderer.list(e, l, a);
                    case "list_item_start":
                        e = "";
                        var o = this.token.loose,
                            h = this.token.checked,
                            u = this.token.task;
                        if (this.token.task)
                            if (o)
                                if ("text" === this.peek().type) {
                                    var c = this.peek();
                                    c.text = this.renderer.checkbox(h) + " " + c.text
                                } else this.tokens.push({
                                    type: "text",
                                    text: this.renderer.checkbox(h)
                                });
                        else e += this.renderer.checkbox(h);
                        for (;
                            "list_item_end" !== this.next().type;) e += o || "text" !== this.token.type ? this.tok() : this.parseText();
                        return this.renderer.listitem(e, u, h);
                    case "html":
                        return this.renderer.html(this.token.text);
                    case "paragraph":
                        return this.renderer.paragraph(this.inline.output(this.token.text));
                    case "text":
                        return this.renderer.paragraph(this.parseText());
                    default:
                        var p = 'Token with "' + this.token.type + '" type was not found.';
                        if (!this.options.silent) throw new Error(p);
                        console.log(p)
                }
            }, n
        }(),
        ne = $,
        re = R,
        se = y,
        ie = s.getDefaults,
        le = s.changeDefaults,
        ae = s.defaults;

    function oe(t, l, a) {
        if (null == t) throw new Error("marked(): input parameter is undefined or null");
        if ("string" != typeof t) throw new Error("marked(): input parameter is of type " + Object.prototype.toString.call(t) + ", string expected");
        if (a || "function" == typeof l) {
            var e = function() {
                a || (a = l, l = null), l = ne({}, oe.defaults, l || {}), re(l);
                var n, r, s = l.highlight,
                    e = 0;
                try {
                    n = B.lex(t, l)
                } catch (e) {
                    return {
                        v: a(e)
                    }
                }
                r = n.length;

                function i(t) {
                    if (t) return l.highlight = s, a(t);
                    var e;
                    try {
                        e = te.parse(n, l)
                    } catch (e) {
                        t = e
                    }
                    return l.highlight = s, t ? a(t) : a(null, e)
                }
                if (!s || s.length < 3) return {
                    v: i()
                };
                if (delete l.highlight, !r) return {
                    v: i()
                };
                for (; e < n.length; e++) ! function(n) {
                    "code" !== n.type ? --r || i() : s(n.text, n.lang, function(e, t) {
                        return e ? i(e) : null == t || t === n.text ? --r || i() : (n.text = t, n.escaped = !0, void(--r || i()))
                    })
                }(n[e]);
                return {
                    v: void 0
                }
            }();
            if ("object" == typeof e) return e.v
        }
        try {
            return l = ne({}, oe.defaults, l || {}), re(l), te.parse(B.lex(t, l), l)
        } catch (e) {
            if (e.message += "\nPlease report this to https://github.com/markedjs/marked.", (l || oe.defaults).silent) return "<p>An error occurred:</p><pre>" + se(e.message + "", !0) + "</pre>";
            throw e
        }
    }
    return oe.options = oe.setOptions = function(e) {
        return ne(oe.defaults, e), le(oe.defaults), oe
    }, oe.getDefaults = ie, oe.defaults = ae, oe.Parser = te, oe.parser = te.parse, oe.Renderer = X, oe.TextRenderer = Q, oe.Lexer = B, oe.lexer = B.lex, oe.InlineLexer = K, oe.inlineLexer = K.output, oe.Slugger = G, oe.parse = oe
});