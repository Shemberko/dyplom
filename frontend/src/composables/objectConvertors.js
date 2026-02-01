export const convertObjectValueBooleanStringToBoolean = (object) => {
    return Object.entries(object).reduce((accumulator, [key, value]) => {
        if (value === 'true') {
            accumulator[key] = true;
        }
        else if (value === 'false') {
            accumulator[key] = false;
        }
        else {
            accumulator[key] = value;
        }
        return accumulator;
    }, {});
};
