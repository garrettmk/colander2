import React from "react";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export const SelectionContext = React.createContext({
    ids: new Set()
});


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class SelectionProvider extends React.Component {

    constructor (props) {
        super(props);

        this.toggleSelected = this.toggleSelected.bind(this);

        this.state = {
            ids: new Set()
        }
    }

    toggleSelected (ids) {
        this.setState({
            ids: new Set(
                Array.from(this.state.ids)
                .filter(v => !ids.includes(v))
                .concat(ids.filter(v => !selection.has(v)))
            )
        })
    }

    render () {
        const { children } = this.props;

        return (
            <SelectionContext.Provider value={{
                ...this.state,
                toggleSelected: this.toggleSelected
            }}>
                {children}
            </SelectionContext.Provider>
        )
    }
}

