"use strict";

function cached (fn) {
  var cache = Object.create(null);
  return function cachedFn (str) {
    var hit = cache[str];
    return hit || (cache[str] = fn(str))
  }
}
Vue.component('bbox-rect', {
  template: '\
<span \
  class="bbox-rect" \
  :class="[{active: value.active, deleted: value.label === -1}, \'label-\' + value.label]" \
  :tabindex="value.label == -1 ? -1 : 0" \
  :style="styleObj" \
  :title="title" \
  ></span>\
    '.trim(),
  methods: {
    // emit: function(event) {
    //   this.$emit(event.type, this.value);
    // },
    dragmove: function(event) {
      var x = event.dx, y = event.dy;
      this.value.x1 += x; this.value.y1 += y;
      this.value.x2 += x; this.value.y2 += y;
    },
    resizemove: function(event) {
      var w, h, x, y;
      var rect = this.value;
      if (event.rect) {
        w = event.rect.width, h = event.rect.height;
        x = event.deltaRect.left, y = event.deltaRect.top;
      } else {
        w = event.clientX - event.clientX0;
        h = event.clientY - event.clientY0;
        if (w >= 0) {
          x = 0;
        } else {
          x = w + rect.x2 - rect.x1;
          // new_x2 = w + rect.x1 + x
          // new_x2 = rect.x2
          w = rect.x2 - rect.x1 - x;
        }
        if (h >= 0) {
          y = 0;
        } else {
          y = h + rect.y2 - rect.y1;
          h = rect.y2 - rect.y1 - y;
        }
      }
      rect.x2 = w + rect.x1 + x;
      rect.y2 = h + rect.y1 + y;
      rect.x1 = Math.max(0, rect.x1 + x);
      rect.y1 = Math.max(0, rect.y1 + y);
      rect.x2 = Math.min(this.maxRight, rect.x2);
      rect.y2 = Math.min(this.maxBottom, rect.y2);
    },
  },
  props: {
    value: {
      type: Object,
      default: function() {
        return {
          id: null,
          x1: 0, y1: 0, x2: 100, y2: 100,
          label: 0
        };
      }
    },
    maxRight: { type: Number, required: true },
    maxBottom: { type: Number, required: true },
    labelNames: { type: Object },
  },
  computed: {
    styleObj: function() {
      var d = this.value;
      return {
        left: d.x1 + 'px', top: d.y1 + 'px',
        width: d.x2 - d.x1 + 'px',
        height: d.y2 - d.y1 + 'px'
      };
    },
    title: function() {
      var label = this.value.label;
      return this.labelNames ? this.labelNames[label] : "";
    },
  }
});
