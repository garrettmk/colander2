import React from "react";
import PropTypes from "prop-types";
import update from "immutability-helper";
import _ from "lodash";
import Colander from "./colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export const QueryContext = React.createContext({
    type: undefined,
    query: undefined,
    view: undefined,
    updateQuery: undefined,
    updateView: undefined
});


export const ObjectContext = React.createContext({
    original: undefined,
    schema: undefined,
    edits: {},
    errors: {},
    loading: false,
    edit: undefined,
    update: undefined,
    save: undefined
});


export const PreviewContext = React.createContext({
    loading: false,
    preview: undefined,
});


export const CollectionContext = React.createContext({
    items: [],
    schema: undefined,
    total: undefined,
    page: undefined,
    pages: undefined,
    per_page: undefined,
    edits: [],
    errors: [],
    loading: [],
    loadingCollection: true,
    edit: undefined,
    update: undefined,
    save: undefined,
    selection: new Set(),
    updateSelection: undefined
});


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class QueryProvider extends React.Component {

    constructor (props) {
        super(props);

        this.updateQuery = this.updateQuery.bind(this);
        this.updateView = this.updateView.bind(this);

        this.state = {
            query: JSON.parse(JSON.stringify(this.props.query)),
            view: JSON.parse(JSON.stringify(this.props.view))
        }
    }

    updateQuery (queryOrCallable) {
        this.setState({
            query: _.isFunction(queryOrCallable) ? queryOrCallable(this.state.query) : queryOrCallable
        })
    }

    updateView (viewOrCallable) {
        this.setState({
            view: _.isFunction(viewOrCallable) ? viewOrCallable(this.state.view) : viewOrCallable
        })
    }

    render () {
        const { type, children } = this.props;

        return (
            <QueryContext.Provider value={{
                type,
                ...this.state,
                updateQuery: this.updateQuery,
                updateView: this.updateView
            }}>
                {children}
            </QueryContext.Provider>
        )
    }
}


QueryProvider.propTypes = {
    type: PropTypes.string,
    query: PropTypes.object,
    view: PropTypes.object
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class ObjectProvider extends React.Component {

    constructor (props) {
        super(props);

        this.fetchObject = this.fetchObject.bind(this);
        this.save = this.save.bind(this);
        this.update = this.update.bind(this);
        this.edit = this.edit.bind(this);

        this.state = {
            original: undefined,
            schema: undefined,
            edits: {},
            errors: {},
            loading: false
        }
    }

    componentDidMount () {
        const { type, id } = this.props;
        if (type && id)
            this.fetchObject();
    }

    componentDidUpdate (prevProps, prevState) {
        if (prevProps.type !== this.props.type
        || prevProps.id !== this.props.id)
            this.fetchObject();
        else if (prevProps.child !== this.props.child)
            this.setState({
                original: undefined,
                edits: {},
                errors: {},
            })
    }

    fetchObject () {
        this.setState({ loading: true });
        const { type, id, view = {} } = this.props;

        Colander.filter(type, {
            query: { id },
            view,

            onSuccess: results => this.setState({
                original: results.items ? results.items[0] : undefined,
                schemas: results.schema ? results.schema.definitions : undefined,
                edits: {},
                errors: results.errors || {},
                loading: false,
            }),

            onFailure: error => { this.setState({
                loading: false,
                errors: { fetch: error }
            }); alert(error); }
        })
    }

    save () {
        this.setState({ loading: true });
        const { type, id } = this.props;
        const { edits } = this.state;

        Colander.update(type, {
            query: { id },
            data: edits,

            onSuccess: results => this.setState({
                loading: false,
                original: update(this.state.original, {$merge: edits}),
                edits: {},
                errors: {},
            }),

            onFailure: error => { this.setState({
                loading: false,
                errors: { save: error }
            }); alert(error) }
        })
    }

    edit (attr, value) {
        this.setState({ edits: update(this.state.edits, {[attr]: {$set: value}}) })
    }

    update (data) {
        this.setState({ edits: update(this.state.edits, {$merge: data}) })
    }

    render () {
        const { type, id, child, children } = this.props;
        const { loading } = this.state;
        const { edit, save, update } = this;
        const funcs = type && id && !loading ? { edit, save, update } : {};

        if (child)
            return (
                <ObjectContext.Consumer>
                    {object => (
                        <ObjectContext.Provider value={{
                            type: object.original && object.original[child] ? (object.original[child].type || type) : type,
                            original: object.original ? object.original[child] : undefined,
                            loading: object.loading
                        }}>
                            { children }
                        </ObjectContext.Provider>
                    )}
                </ObjectContext.Consumer>
            );

        else
            return (
                <ObjectContext.Provider value={{
                    type,
                    ...this.state,
                    ...funcs
                }}>
                    { children }
                </ObjectContext.Provider>
            )
    }
}


ObjectProvider.propTypes = {
    type: PropTypes.string,
    id: PropTypes.number,
    child: PropTypes.string,
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class PreviewProvider extends React.Component {

    constructor (props) {
        super(props);

        this.fetchPreview = this.fetchPreview.bind(this);

        this.state = {
            loading: false,
            preview: undefined,
        }
    }

    componentDidMount () { this.fetchPreview() }

    componentDidUpdate (prevProps) {
        const { type, id } = this.props;

        if (prevProps.type !== type || prevProps.id !== id)
            this.fetchPreview();
    }

    fetchPreview () {
        const { type, id } = this.props;

        if (!type || !id)
            return this.setState({ loading: false, preview: undefined });

        this.setState({ loading: true });

        Colander.filter(type, {
            query: { id },
            schema: 'Preview',

            onSuccess: results => {
                this.setState({
                    loading: false,
                    preview: results.items ? results.items[0] : undefined
                })
            },

            onFailure: error => {
                this.setState({
                    loading: false,
                    preview: undefined,
                })
            }
        })
    }

    render () {
        const { children } = this.props;

        return (
            <PreviewContext.Provider value={{
                ...this.state
            }}>
                {children}
            </PreviewContext.Provider>
        );
    }
}


PreviewProvider.propTypes = {
    type: PropTypes.string,
    id: PropTypes.integer,
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class CollectionProvider extends React.Component {

    constructor (props) {
        super(props);

        this.fetchObjects = this.fetchObjects.bind(this);
        this.save = this.save.bind(this);
        this.edit = this.edit.bind(this);
        this.update = this.update.bind(this);
        this.updateSelection = this.updateSelection.bind(this);
        this.toggleSelected = this.toggleSelected.bind(this);

        this.state = {
            items: [],
            schemas: {},
            total: undefined,
            page: undefined,
            pages: undefined,
            per_page: undefined,
            edits: [],
            errors: [],
            loading: [],
            loadingCollection: true,
            selection: new Set()
        }
    }

    componentDidMount () { this.fetchObjects() }
    componentDidUpdate (prevProps) { }

    fetchObjects () {
        this.setState({ loadingCollection: true });
        const { type, query, view } = this.props;

        Colander.filter(type, {
            query,
            view,

            onSuccess: results => this.setState({
                ...results,
                schema: results.schema ? results.schema.definitions : undefined,
                edits: [],
                errors: [],
                loading: [],
                loadingCollection: false,
            }),

            onFailure: error => { this.setState({
                loadingCollection: false,
                errors: { fetch: error }
            }); alert(error); }
        })
    }

    save (index) {
        const { type } = this.props;
        const start = index === undefined ? 0 : index;

        let edits, id;
        for (let i=start; i<this.state.items.length; i++) {
            this.setState({ loading: this.state.loading.map((ld, idx) => idx === i ? true : ld) });

            edits = this.state.edits[i];
            id = this.state.items[i];

            Colander.update(type, {
                query: { id },
                data: edits,

                onSuccess: results => 'errors' in results
                    ? this.setState(current => ({
                        loading: current.loading.map((ld, idx) => idx === i ? false : ld),
                        errors: current.errors.map((err, idx) => idx === i ? results.errors : err)
                    }))
                    : this.setState(current => ({
                        loading: current.loading.map((ld, idx) => idx === i ? false : ld),
                        items: current.items.map((item, idx) => idx === i ? update(item, {$merge: edits}) : item),
                        edits: current.edits.map((edit, idx) => idx === i ? {} : edit)
                    })),

                onFailure: error => this.setState(current => ({
                    loading: current.loading.map((ld, idx) => idx === i ? false : ld),
                    errors: current.errors.map((err, idx) => idx === i ? {fetch: error} : err)
                }))
            });

            if (index !== undefined) break;
        }
    }

    edit (attr, value, index=0) {
        this.setState(current => ({
            edits: current.edits.map((edt, idx) => idx === index ? update(edt, {$merge: {[attr]: value}}) : edt)
        }))
    }

    update (merge, index=0) {
        this.setState(current => ({
            items: current.items.map((item, idx) => idx === index ? update(item, {$merge: merge}) : item)
        }))
    }

    updateSelection (upd) {
        this.setState({ selection: update(this.state.selection, upd)})
    }

    toggleSelected (ids) {
        const { selection } = this.state;

        this.setState({
            selection: new Set(selection.values()
                .filter(v => !ids.includes(v))
                .concat(ids.filter(v => !selection.includes(v)))
            )
        })
    }

    render () {
        const { children, type } = this.props;

        return (
            <CollectionContext.Provider value={{
                ...this.state,
                type,
                save: this.save,
                edit: this.edit,
                update: this.update,
                updateSelection: this.updateSelection,
                toggleSelected: this.toggleSelected
            }}>
                {children}
            </CollectionContext.Provider>
        )
    }
}


CollectionProvider.propTypes = {
    type: PropTypes.string,
    query: PropTypes.object,
    view: PropTypes.object
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function IndexProvider (props) {
    const { index, children } = props;

    return (
        <CollectionContext.Consumer>
            {collection => {
                const original = collection.items ? collection.items[index] : undefined;
                const schema = collection.schema;
                const edits = collection.edits ? collection.edits[index] : undefined;
                const errors = collection.errors ? collection.errors[index] : undefined;
                const type = collection.type;

                const loading = collection.loadingCollection || collection.loading[index];

                return (
                    <ObjectContext.Provider value={{
                        original,
                        schema,
                        edits,
                        errors,
                        loading,
                        type,

                        save: () => collection.save(index),
                        edit: (attr, value) => collection.edit(attr, value, index, node),
                        update: upd => collection.update(upd)
                    }}>
                        { children }
                    </ObjectContext.Provider>
                )}
            }}
        </CollectionContext.Consumer>
    )
}

