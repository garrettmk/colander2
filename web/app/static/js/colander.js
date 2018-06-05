
function makeGetAttrs (getAttrs, def = 'all') {
    if (getAttrs)
        return getAttrs.map(attr => 'getAttrs=' + attr).join('&')
    else
        return `getAttrs=${def}`
}

export function fetchVendor (id, options = { getAttrs: ['all'] }) {
    const params = makeGetAttrs(options.getAttrs);
    return fetch(`/api/obj/vendor?id=${id}&${params}`)
}

export function fetchVendorNames (onSuccess, onError) {
    fetch('/api/obj/vendor?getAttrs=id&getAttrs=name').then(response => {
        if (!response.ok)
            onError(new Error('fetchVendorNames failed.'));

        return response.json();
    }).then(results => {
        let obj = {};
        results.items.forEach(result => {
            obj[result.id] = result.name;
        });
        onSuccess(obj)
    }).catch(e => {
        if (onError)
            onError(e);
        else
            throw e;
    })
}

export function fetchListing (listingId, options = { getAttrs: ['all'] }) {
    const params = makeGetAttrs(options.getAttrs);
    return fetch(`/api/obj/listing?id=${listingId}&${params}`)
}

