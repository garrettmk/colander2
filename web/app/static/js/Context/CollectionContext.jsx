import React from "react";
import PropTypes from "prop-types";
import update from "immutability-helper";
import _ from "lodash";
import Colander from "../colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export const CollectionContext = React.createContext({
    items: [],
    schemas: undefined,
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
    componentDidUpdate (prevProps, prevState) {
        const { query, view, type } = this.props;

        if (prevProps.type !== type
            || !_.isEqual(prevProps.view, view)
            || !_.isEqual(prevProps.query, query))
            this.fetchObjects();
    }

    fetchObjects () {
        this.setState({ loadingCollection: true });
        const { type, query, view } = this.props;

        Colander.filter(type, {
            query,
            view,

            onSuccess: results => this.setState({
                ...results,
                schemas: results.schema ? results.schema.definitions : {},
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
            selection: new Set(
                Array.from(selection)
                .filter(v => !ids.includes(v))
                .concat(ids.filter(v => !selection.has(v)))
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
            { ({ items, schemas, edits, errors, type, loading, loadingCollection }) => {
                const original = items ? items[index] : undefined;
                const idxLoading = loadingCollection || loading[index];

                return (
                    <DocumentProvider
                        doc={original}
                        schemas={schemas}
                        type={type}
                        loading={idxLoading}
                        index={index}
                    >
                        {children}
                    </DocumentProvider>
                )
            }}
        </CollectionContext.Consumer>
    )
}

