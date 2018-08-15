import React from "react";
import PropTypes from "prop-types";
import _ from "lodash";
import update from "immutability-helper";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export const DocumentContext = React.createContext({
    original: undefined,
    edited: undefined,
    schema: {},
    edits: {},
    edit: undefined,
    update: undefined,
    save: undefined
});


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function DocumentProvider (props) {
    const { children, ...values } = props;
    return (
        <DocumentContext.Provider value={{...values}}>
            {children}
        </DocumentContext.Provider>
    )
}


DocumentProvider.propTypes = {
    doc: PropTypes.object,
};


DocumentProvider.defaultProps = {
    doc: {},
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function NestedDocProvider (props) {
    const { node, children, ...extras } = props;

    return (
        <DocumentContext.Consumer>
            { ({ doc, schemas }) => (
                <DocumentProvider doc={doc[node]} schemas={schemas} {...extras}>
                    {children}
                </DocumentProvider>
            )}
        </DocumentContext.Consumer>
    )
}


NestedDocProvider.propTypes = {
    node: PropTypes.string.isRequired,
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class EditableDocProvider extends React.Component {

    constructor (props) {
        super(props);

        this.edit = this.edit.bind(this);
        this.save = this.save.bind(this);

        this.state = {
            edits: {}
        }
    }

    componentDidUpdate (prevProps) {
        if (!_.isEqual(prevProps.doc, this.props.doc))
            this.setState({ edits: {} });
    }

    edit (attr, value) {
        const { edits } = this.state;
        const { doc, onEdit } = this.props;

        const newEdits = doc && doc[attr] === value
            ? update(edits, { $unset: [attr] })
            : update(edits, { [attr]: { $set: value } });

        this.setState({ edits: newEdits });
        onEdit && onEdit(attr, value);
    }

    save () {
        const { onSave } = this.props;
        onSave ? onSave(this.state.edits) : null;
    }

    render () {
        const { edit, save } = this;
        const { edits }  = this.state;
        const { doc, onSave, children, ...extras } = this.props;
        const edited = doc ? update(doc, { $merge: edits }) : undefined;
        const params = {
            doc,
            edited,
            edits,
            edit,
            save,
            ...extras
        };

        return (
            <DocumentProvider {...params}>
                {children}
            </DocumentProvider>
        )
    }
}


EditableDocProvider.propTypes = {
    doc: PropTypes.object,
    onSave: PropTypes.func
};


EditableDocProvider.defaultProps = {
    doc: {}
};
