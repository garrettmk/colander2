import React from "react";
import PropTypes from "prop-types";
import _ from "lodash";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export const QueryContext = React.createContext({
    type: undefined,
    query: undefined,
    view: undefined,
    updateQuery: undefined,
    updateView: undefined
});


export class QueryProvider extends React.Component {

    constructor (props) {
        super(props);

        this.setQuery = this.setQuery.bind(this);
        this.setView = this.setView.bind(this);

        this.state = {
            query: JSON.parse(JSON.stringify(this.props.query)),
            view: JSON.parse(JSON.stringify(this.props.view))
        }
    }

    setQuery (queryOrCallable) {
        this.setState({
            query: _.isFunction(queryOrCallable) ? queryOrCallable(this.state.query) : queryOrCallable
        })
    }

    setView (viewOrCallable) {
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
                setQuery: this.setQuery,
                setView: this.setView
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

