import React from "react";
import PropTypes from "prop-types";
import _ from "lodash";

import { DocumentProvider } from "./DocumentContext";
import Colander from "../colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export const CollectionContext = React.createContext({
    items: [],
    schemas: undefined,
    total: undefined,
    loading: false,
});


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class CollectionProvider extends React.Component {

    constructor (props) {
        super(props);

        this.fetchObjects = this.fetchObjects.bind(this);

        this.state = {
            items: [],
            schemas: {},
            loading: false,
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
        this.setState({ loading: true });
        const { type, query, view } = this.props;

        Colander.filter(type, {
            query,
            view,

            onSuccess: results => this.setState({
                ...results,
                schemas: results.schema ? results.schema.definitions : {},
                loading: false,
            }),

            onFailure: error => { this.setState({
                loading: false,
            }); alert(error); }
        })
    }

    render () {
        const { children, type } = this.props;

        return (
            <CollectionContext.Provider value={{
                ...this.state,
                type,
            }}>
                {children}
            </CollectionContext.Provider>
        )
    }
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


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
            { ({ items, schemas, type, loading }) => {
                const original = items ? items[index] : undefined;

                return (
                    <DocumentProvider
                        doc={original}
                        schemas={schemas}
                        type={type}
                        loading={loading}
                        index={index}
                    >
                        {children}
                    </DocumentProvider>
                )
            }}
        </CollectionContext.Consumer>
    )
}

