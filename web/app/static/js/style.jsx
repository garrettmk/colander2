////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// Style options used by various components.


export const defaultImages = {
    Vendor: {
        light: 'https://imgplaceholder.com/128x128/transparent/757575/fa-globe',
        dark: 'https://imgplaceholder.com/128x128/transparent/ffffff/fa-globe',
    },
    Listing: {
        light: 'https://imgplaceholder.com/128x128/transparent/757575/fa-barcode',
        dark: 'https://imgplaceholder.com/128x128/transparent/ffffff/fa-barcode'
    },
    Customer: {
        light: 'https://imgplaceholder.com/128x128/transparent/757575/ion-android-person',
        dark: 'https://imgplaceholder.com/128x128/transparent/ffffff/ion-android-person',
    },
    Extension: {
        light: 'https://imgplaceholder.com/128x128/transparent/757575/fa-gears',
        dark: 'https://imgplaceholder.com/128x128/transparent/ffffff/fa-gears'
    }
};

export const defaultImage = {
    light: 'https://imgplaceholder.com/128x128/transparent/757575/fa-question-circle-o',
    dark: 'https://imgplaceholder.com/128x128/transparent/ffffff/fa-question-circle-o'
};


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



