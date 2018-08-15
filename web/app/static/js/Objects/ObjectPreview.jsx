import React from "react";
import PropTypes from "prop-types";

import { Item, Button, Modal, Icon } from "semantic-ui-react";

import { DocumentContext } from "../Context/DocumentContext";
import ObjectSearchBox from "./ObjectSearchBox";
import { defaultImage, defaultImages } from "../style";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default class ObjectPreview extends React.Component {

    constructor (props) {
        super(props);

        this.handleSearch = this.handleSearch.bind(this);
        this.handleResultSelect = this.handleResultSelect.bind(this);

        this.state = { searching: false }
    }

    handleSearch () { this.setState({ searching: true })};

    handleResultSelect (result) {
        const { onChange } = this.props;
        if (onChange) onChange(result.id);
        this.setState({ searching: false });
    }

    render () {
        const { small, onChange} = this.props;
        const { searching } = this.state;

        return (
            <DocumentContext.Consumer>
                { ({ preview, type }) => (
                    <React.Fragment>
                        <Item.Group>
                            <Item>
                                <Item.Image size={small ? 'mini' : 'small'} src={preview
                                    ? preview.image
                                        ? preview.image
                                        : defaultImages[type]
                                    : defaultImage
                                }/>

                                <Item.Content>
                                    {onChange
                                        ? <Button circular floated={'right'} icon={'search'} onClick={this.handleSearch}/>
                                        : <React.Fragment/>
                                    }
                                    <Item.Header className={small ? 'ui tiny' : ''}>{preview
                                        ? preview.title
                                            ? preview.title
                                            : 'n/a'
                                        : 'None selected'
                                    }</Item.Header>

                                    <Item.Meta>{preview
                                        ? preview.description
                                        : 'Click to search...'
                                    }</Item.Meta>
                                    {preview && preview.url &&
                                        <Item.Extra as={'a'} href={preview.url}>{preview.url} <Icon name={'external'}/></Item.Extra>
                                    }
                                </Item.Content>
                            </Item>
                        </Item.Group>
                        <Modal basic size={'tiny'} open={searching}>
                            <Modal.Header>Select Object</Modal.Header>
                            <Modal.Content>
                                <ObjectSearchBox
                                    fluid
                                    input={{fluid: true}}
                                    types={[type]}
                                    onResultSelect={this.handleResultSelect}
                                />
                            </Modal.Content>
                            <Modal.Actions>
                                <Button
                                    basic
                                    inverted
                                    negative
                                    color={'red'}
                                    icon={'remove'}
                                    onClick={() => this.handleResultSelect({ id: null })}
                                    content={'Clear Selection'}
                                />
                            </Modal.Actions>
                        </Modal>
                    </React.Fragment>
                )}
            </DocumentContext.Consumer>
        )
    }
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


ObjectPreview.propTypes = {
    small: PropTypes.bool,
    onChange: PropTypes.func,
};
