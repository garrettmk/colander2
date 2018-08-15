////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// Style options used by various components.


export const defaultImages = {
    Vendor: 'https://imgplaceholder.com/128x128/cccccc/757575/fa-globe',
    Customer: 'https://imgplaceholder.com/128x128/cccccc/757575/ion-android-person',
    Extension: 'https://imgplaceholder.com/128x128/cccccc/757575/fa-gears'
};

export const defaultImage = 'https://imgplaceholder.com/128x128/cccccc/757575/fa-question-circle-o';


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function asCurrency(value) {
    try {
        if (typeof value === 'string')
            value = parseFloat(value);

        return value.toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD'
        })
    } catch (e) {
        return 'n/a'
    }
}

export function asCount(value) {
        try {
            if (typeof value === 'string')
                value = parseInt(value);
            return value.toLocaleString('en-US');
        } catch (e) {
            return 'n/a'
        }

}

export function asPercent(value) {
    try {
        if (typeof value === 'string')
            value = parseFloat(value);
        return (value * 100).toLocaleString('en-US') + '%'
    } catch (e) {
        return 'n/a'
    }
}



