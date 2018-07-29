import queryString from "query-string";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const Colander = {
    urlPrefix: '/api',

    post: function (url, { onSuccess, onFailure, ...bodyObj }) {
        const prefixedUrl = Colander.urlPrefix + url;
        const body = JSON.stringify(bodyObj);

        fetch(prefixedUrl, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body
        }).then(response => {
            if (response.ok)
                return response.json();
            throw new Error(`Could not fetch data: ${prefixedUrl}`)
        }).then(results => onSuccess ? onSuccess(results) : null)
          .catch(error => onFailure ? onFailure(error) : null)
    },

    get: function (url, { onSuccess, onFailure, ...params }) {
        const prefixedUrl = Colander.urlPrefix + url;
        const qs = '?' + queryString.stringify(params);

        fetch(prefixedUrl + qs).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch data: ' + prefixedUrl + qs)
        }).then(results => onSuccess ? onSuccess(results) : null)
          .catch(error => onFailure ? onFailure(error) : null);
    },


    schema: function (type, options) { Colander.post(`/${type}/schema`, options) },
    filter: function (type, options) { Colander.post(`/${type}/filter`, options) },
    update: function (type, options) { Colander.post(`/${type}/update`, options) },
    create: function (type, options) { Colander.post(`/${type}/create`, options) },
    delete_: function (type, options) { Colander.post(`/$${type}/delete`, options) },
    quick: function (options) { Colander.get('/quick', options) },
    sendTask: function (options) { Colander.post('/tasks', options)}
};


export default Colander;