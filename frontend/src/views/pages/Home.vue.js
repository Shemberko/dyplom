import { useUserStore } from '@/stores/user';
import { storeToRefs } from 'pinia';
import { api } from '@/composables/api';
const userStore = useUserStore();
const { isAuthenticated, user } = storeToRefs(userStore);
const { ensureAuth } = api();
// Приклад: функція, яка може бути викликана для ініціації SSO з кнопки
const handleLoginClick = async () => {
    try {
        await ensureAuth();
        console.log('Авторизація ініційована успішно.');
    }
    catch (e) {
        console.error('Не вдалося ініціювати вхід:', e);
    }
};
const __VLS_ctx = {
    ...{},
    ...{},
};
let ___VLS_components;
let ___VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "home-container" },
});
/** @type {__VLS_StyleScopedClasses['home-container']} */ ;
__VLS_asFunctionalElement(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
if (__VLS_ctx.isAuthenticated) {
    __VLS_asFunctionalElement(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "welcome-message" },
    });
    /** @type {__VLS_StyleScopedClasses['welcome-message']} */ ;
    __VLS_asFunctionalElement(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    (__VLS_ctx.user.email);
    __VLS_asFunctionalElement(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    let __VLS_0;
    /** @ts-ignore @type {typeof ___VLS_components.routerLink | typeof ___VLS_components.RouterLink} */
    routerLink;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
        to: "/recommendations",
    }));
    const __VLS_2 = __VLS_1({
        to: "/recommendations",
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    const { default: __VLS_5 } = __VLS_3.slots;
    // @ts-ignore
    [isAuthenticated, user,];
    var __VLS_3;
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "sso-guide" },
    });
    /** @type {__VLS_StyleScopedClasses['sso-guide']} */ ;
    __VLS_asFunctionalElement(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement(__VLS_intrinsics.ol, __VLS_intrinsics.ol)({});
    __VLS_asFunctionalElement(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    __VLS_asFunctionalElement(__VLS_intrinsics.li, __VLS_intrinsics.li)({});
    __VLS_asFunctionalElement(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.handleLoginClick) },
        ...{ class: "login-button" },
    });
    /** @type {__VLS_StyleScopedClasses['login-button']} */ ;
}
// @ts-ignore
[handleLoginClick,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
