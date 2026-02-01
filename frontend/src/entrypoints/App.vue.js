import { useUserStore } from '@/stores/user';
import { useRouter } from 'vue-router';
// import Notification from './components/Notification.vue';
const userStore = useUserStore();
const router = useRouter();
userStore.initializeAuth();
const __VLS_ctx = {
    ...{},
    ...{},
};
let ___VLS_components;
let ___VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    id: "app-container",
});
__VLS_asFunctionalElement(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "app-header" },
});
/** @type {__VLS_StyleScopedClasses['app-header']} */ ;
__VLS_asFunctionalElement(__VLS_intrinsics.nav, __VLS_intrinsics.nav)({});
let __VLS_0;
/** @ts-ignore @type {typeof ___VLS_components.routerLink | typeof ___VLS_components.RouterLink} */
routerLink;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    to: "/",
}));
const __VLS_2 = __VLS_1({
    to: "/",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const { default: __VLS_5 } = __VLS_3.slots;
var __VLS_3;
if (__VLS_ctx.userStore.isAuthenticated) {
    let __VLS_6;
    /** @ts-ignore @type {typeof ___VLS_components.routerLink | typeof ___VLS_components.RouterLink} */
    routerLink;
    // @ts-ignore
    const __VLS_7 = __VLS_asFunctionalComponent(__VLS_6, new __VLS_6({
        to: "/recommendations",
    }));
    const __VLS_8 = __VLS_7({
        to: "/recommendations",
    }, ...__VLS_functionalComponentArgsRest(__VLS_7));
    const { default: __VLS_11 } = __VLS_9.slots;
    // @ts-ignore
    [userStore,];
    var __VLS_9;
}
if (__VLS_ctx.userStore.isAuthenticated) {
    __VLS_asFunctionalElement(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.userStore.isAuthenticated))
                    return;
                __VLS_ctx.userStore.logOut();
                // @ts-ignore
                [userStore, userStore,];
            } },
    });
    (__VLS_ctx.userStore.user.email);
}
__VLS_asFunctionalElement(__VLS_intrinsics.main, __VLS_intrinsics.main)({
    ...{ class: "app-main" },
});
/** @type {__VLS_StyleScopedClasses['app-main']} */ ;
let __VLS_12;
/** @ts-ignore @type {typeof ___VLS_components.routerView | typeof ___VLS_components.RouterView} */
routerView;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({}));
const __VLS_14 = __VLS_13({}, ...__VLS_functionalComponentArgsRest(__VLS_13));
// @ts-ignore
[userStore,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
